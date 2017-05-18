#!python
#cython: embedsignature=True, language_level=3
"""
Audio Library

This library requires both the SDL2 and SDL_Mixer libraries.
"""

__all__ = ('AudioInterface',
           'AudioException',
           'Track',
           'MixChunkContainer',
           )

from libc.stdio cimport FILE, fopen, fprintf, sprintf
from libc.stdlib cimport malloc, free, calloc
from libc.string cimport memset, memcpy
from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
cimport cpython.pycapsule as pycapsule
import cython

from heapq import heappush, heappop, heapify
from math import pow
import time
import logging
import os


include "sdl2.pxi"
include "gstreamer.pxi"
include "audio_interface.pxi"

# ---------------------------------------------------------------------------
#    Various audio engine setting values
# ---------------------------------------------------------------------------
DEF MAX_TRACKS = 8
DEF MAX_SIMULTANEOUS_SOUNDS_DEFAULT = 8
DEF MAX_SIMULTANEOUS_SOUNDS_LIMIT = 32
DEF QUICK_FADE_DURATION_SECS = 0.05


# ---------------------------------------------------------------------------
#    AudioException class
# ---------------------------------------------------------------------------
class AudioException(Exception):
    """Exception returned by the audio module"""
    pass


# ---------------------------------------------------------------------------
#    Global GStreamer helper functions
# ---------------------------------------------------------------------------
def _gst_init():
    """Initializes the GStreamer library"""
    if gst_is_initialized():
        return True
    cdef int argc = 0
    cdef char **argv = NULL
    cdef GError *error
    if not gst_init_check(&argc, &argv, &error):
        msg = 'Unable to initialize GStreamer: code={} message={}'.format(
                error.code, <bytes>error.message)
        raise AudioException(msg)

def get_gst_version():
    """Returns the current version of GStreamer"""
    cdef unsigned int major, minor, micro, nano
    gst_version(&major, &minor, &micro, &nano)
    return major, minor, micro, nano


# ---------------------------------------------------------------------------
#    AudioInterface class
# ---------------------------------------------------------------------------
cdef class AudioInterface:
    """
    The AudioInterface class provides a management wrapper around the SDL2 and SDL_Mixer
    libraries.
    """
    cdef int supported_formats
    cdef list tracks
    cdef object mc
    cdef object log

    cdef AudioCallbackData audio_callback_data

    def __cinit__(self, *args, **kw):
        self.supported_formats = 0

    def __init__(self, rate=44100, channels=2, buffer_samples=4096):
        """
        Initializes the AudioInterface.
        Args:
            rate: The audio sample rate used in the library
            channels: The number of channels to use (1=mono, 2=stereo)
            buffer_samples: The audio buffer size to use (in number of samples, must be power of two)
        """
        cdef SDL_AudioSpec desired
        cdef SDL_AudioSpec obtained
        self.log = logging.getLogger("AudioInterface")

        # Initialize threading in the extension library and acquire the Python global interpreter lock
        PyEval_InitThreads()

        # Make sure buffer samples is a power of two (required by SDL2)
        if not AudioInterface.power_of_two(buffer_samples):
            self.log.error('Buffer samples is required to be a power of two')
            raise AudioException("Unable to initialize Audio Interface: "
                                 "Buffer samples is required to be a power of two")

        # Warn if a small buffer is used
        if buffer_samples <= 1024:
            self.log.warning('NOTE: You may experience noise and other undesirable sound artifacts '
                             'when you set your buffer at 1024 or smaller.')

        # Initialize the SDL audio system
        if SDL_Init(SDL_INIT_AUDIO) < 0:
            self.log.error('SDL_Init error - %s' % SDL_GetError())
            raise AudioException('Unable to initialize SDL (SDL_Init call failed: %s)' % SDL_GetError())

        # Set the desired audio interface settings to request from SDL
        desired.freq = rate
        desired.format = AUDIO_S16SYS
        desired.channels = channels
        desired.samples = buffer_samples
        desired.callback = AudioInterface.audio_callback
        desired.userdata = &self.audio_callback_data

        # Open the audio device using the desired settings
        self.audio_callback_data.device_id = SDL_OpenAudioDevice(NULL, 0, &desired, &obtained, SDL_AUDIO_ALLOW_FREQUENCY_CHANGE | SDL_AUDIO_ALLOW_CHANNELS_CHANGE)
        if self.audio_callback_data.device_id == 0:
            self.log.error('SDL_OpenAudioDevice error - %s' % SDL_GetError())
            raise AudioException('Unable to open audio for output (SDL_OpenAudioDevice failed: %s)' % SDL_GetError())

        # Initialize the SDL_Mixer library to establish the output audio format and encoding
        # (sample rate, bit depth, buffer size).
        # NOTE: SDL_Mixer is only used to load audio files into memory and not for any output functions. This
        if Mix_OpenAudio(obtained.freq, obtained.format, obtained.channels, obtained.samples):
            self.log.error('Mix_OpenAudio error - %s' % SDL_GetError())
            raise AudioException('Unable to open SDL_Mixer library for loading audio files (Mix_OpenAudio failed: %s)' % SDL_GetError())

        # We want to use as little resources as possible for SDL_Mixer (since it is just used for loading)
        Mix_AllocateChannels(0)

        # Initialize GStreamer
        self._initialize_gstreamer()

        self.log.info("Initialized")
        self.log.debug("Loaded %s", AudioInterface.get_sdl_version())
        self.log.debug("Loaded %s", AudioInterface.get_sdl_mixer_version())
        self.log.debug("Loaded %s", AudioInterface.get_gstreamer_version())
        self.log.debug("Loaded %s", AudioInterface.get_glib_version())

        # Store the actual audio format in use by the opened audio device.  This may or may not match
        # the requested values used to initialize the audio interface.  A pointer to the audio_callback_data
        # structure is passed to the SDL audio callback function and is the source of all audio state
        # and mixing data needed to generate the output signal.
        self.audio_callback_data.sample_rate = obtained.freq
        self.audio_callback_data.channels = obtained.channels
        self.audio_callback_data.format = obtained.format
        self.audio_callback_data.buffer_samples = obtained.samples
        self.audio_callback_data.buffer_size = obtained.size
        self.audio_callback_data.bytes_per_control_point = obtained.size // CONTROL_POINTS_PER_BUFFER
        self.audio_callback_data.bytes_per_sample = SDL_AUDIO_BITSIZE(obtained.format) // 8
        self.audio_callback_data.seconds_to_bytes_factor = self.audio_callback_data.sample_rate * self.audio_callback_data.channels * self.audio_callback_data.bytes_per_sample
        self.audio_callback_data.master_volume = SDL_MIX_MAXVOLUME // 2
        self.audio_callback_data.quick_fade_steps = (<int>(QUICK_FADE_DURATION_SECS *
                                                     self.audio_callback_data.sample_rate *
                                                     self.audio_callback_data.channels *
                                                     self.audio_callback_data.bytes_per_sample
                                                           )) // self.audio_callback_data.bytes_per_control_point
        self.audio_callback_data.silence = obtained.silence
        self.audio_callback_data.track_count = 0
        self.audio_callback_data.tracks = <TrackState**> PyMem_Malloc(MAX_TRACKS * sizeof(TrackState*))
        self.audio_callback_data.c_log_file = NULL
        #self.audio_callback_data.c_log_file = fopen("D:\\Temp\\Dev\\MPFMC_AudioLibrary.log", "wb")

        self.log.debug('Settings requested - rate: %d, channels: %d, buffer: %d samples',
                       rate, channels, buffer_samples)
        self.log.debug('Settings in use - rate: %d, channels: %d, buffer: %d samples (%d bytes @ %d bytes per sample)',
                       self.audio_callback_data.sample_rate, self.audio_callback_data.channels,
                       self.audio_callback_data.buffer_samples, self.audio_callback_data.buffer_size,
                       self.audio_callback_data.bytes_per_sample)

        self.tracks = list()

    def __del__(self):
        """Shut down the audio interface and clean up allocated memory"""
        self.log.debug("Shutting down and cleaning up allocated memory...")

        # Stop audio processing (will stop all SDL callbacks)
        self.shutdown()

        # Remove tracks
        self.tracks.clear()

        PyMem_Free(self.audio_callback_data.tracks)

        # SDL and SDL_Mixer no longer needed
        Mix_Quit()
        SDL_Quit()

    def _initialize_gstreamer(self):
        """Initialize the GStreamer library"""
        if gst_is_initialized():
            return True

        cdef int argc = 0
        cdef char **argv = NULL
        cdef GError *error
        if not gst_init_check(&argc, &argv, &error):
            msg = 'Unable to initialize gstreamer: code={} message={}'.format(error.code, <bytes>error.message)
            raise AudioException(msg)

    @staticmethod
    def initialize(int rate=44100, int channels=2, int buffer_samples=4096, **kwargs):
        """
        Initializes and retrieves the audio interface instance.
        Args:
            rate: The audio sample rate used in the library
            channels: The number of channels to use (1=mono, 2=stereo)
            buffer_samples: The audio buffer size in number of samples (must be power of two)

        Returns:
            An AudioInterface object instance.
        """
        # Initialize the audio instance and return it
        audio_interface_instance = AudioInterface(rate=rate,
                                                  channels=channels,
                                                  buffer_samples=buffer_samples,
                                                  **kwargs)
        return audio_interface_instance

    @staticmethod
    def power_of_two(int num):
        """ Returns whether or not the supplied number is a power of 2 """
        return ((num & (num - 1)) == 0) and num != 0

    @staticmethod
    def db_to_gain(float db):
        """Converts a value in decibels (-inf to 0.0) to a gain (0.0 to 1.0)"""
        return pow(10, db / 20.0)

    @staticmethod
    def string_to_gain(gain):
        """Converts a string to a gain value (0.0 to 1.0)"""
        cdef str gain_string = str(gain).upper()

        if gain_string.endswith('DB'):
            gain_string = ''.join(i for i in gain_string if not i.isalpha())
            return min(max(AudioInterface.db_to_gain(float(gain_string)), 0.0), 1.0)

        return min(max(float(gain_string), 0.0), 1.0)

    def convert_seconds_to_samples(self, float seconds):
        """Converts the specified number of seconds into samples (based on current sample rate)"""
        return int(self.audio_callback_data.sample_rate * seconds)

    def convert_seconds_to_buffer_length(self, float seconds):
        """Convert the specified number of seconds into a buffer length (based on current
        sample rate, the number of audio channels, and the number of bytes per sample)."""
        return int(seconds * self.audio_callback_data.sample_rate * self.audio_callback_data.channels * self.audio_callback_data.bytes_per_sample)

    def convert_buffer_length_to_seconds(self, int buffer_length):
        """Convert the specified buffer length into a time in seconds (based on current
        sample rate, the number of audio channels, and the number of bytes per sample)."""
        return round(buffer_length / (self.audio_callback_data.sample_rate * self.audio_callback_data.channels * self.audio_callback_data.bytes_per_sample), 3)

    @staticmethod
    def string_to_secs(time):
        """Decodes a string of real-world time into a float of seconds.
        Example inputs:

        234ms
        2s
        None

        If no "s" or "ms" is provided, this method assumes "seconds."

        If time is 'None' or a string of 'None', this method returns 0.0.

        Returns:
            Float. The examples listed above return 0.234, 2.0 and 0.0,
            respectively
        """
        cdef str time_string = str(time).upper()

        if time_string.endswith('MS') or time_string.endswith('MSEC'):
            time_string = ''.join(i for i in time_string if not i.isalpha())
            return float(time_string) / 1000.0

        elif time_string.endswith('S') or time_string.endswith('SEC'):
            time_string = ''.join(i for i in time_string if not i.isalpha())
            return float(time_string)

        elif 'D' in time_string:
            time_string = ''.join(i for i in time_string if not i.isalpha())
            return float(time_string) * 86400

        elif 'H' in time_string:
            time_string = ''.join(i for i in time_string if not i.isalpha())
            return float(time_string) * 3600

        elif 'M' in time_string:
            time_string = ''.join(i for i in time_string if not i.isalpha())
            return float(time_string) * 60

        elif not time_string or time_string == 'NONE':
            return 0.0

        else:
            try:
                return float(time_string)
            except:
                return 0.0

    def string_to_samples(self, samples):
        """
        Converts a string to an integer value representing the number of samples.
        Args:
            samples: String containing either a time string or an integer number
                of samples.

        Returns:
            Integer containing the number of samples.
        """
        cdef str samples_string = str(samples).upper()

        # If the string contains only digits we assume it is already in samples
        try:
            return int(float(samples_string))
        except:
            pass

        # Time strings are also permitted and will be converted to seconds
        # and then to samples using the current sample rate.
        cdef float seconds = AudioInterface.string_to_secs(samples_string)
        return int(self.audio_callback_data.sample_rate * seconds)

    @classmethod
    def get_sdl_version(cls):
        """
        Returns the version of the SDL library
        :return: SDL library version string
        """
        cdef SDL_version version
        SDL_GetVersion(&version)
        return 'SDL {}.{}.{}'.format(version.major, version.minor, version.patch)

    @classmethod
    def get_sdl_mixer_version(cls):
        """
        Returns the version of the dynamically linked SDL_Mixer library
        :return: SDL_Mixer library version string
        """
        cdef const SDL_version *version = Mix_Linked_Version()
        return 'SDL_Mixer {}.{}.{}'.format(version.major, version.minor, version.patch)

    @classmethod
    def get_gstreamer_version(cls):
        """
        Returns the version of the GStreamer library
        :return: GStreamer library version string
        """
        gst_version = get_gst_version()
        return 'GStreamer {}.{}.{}.{}'.format(
            gst_version[0], gst_version[1], gst_version[2], gst_version[3])

    @classmethod
    def get_glib_version(cls):
        """
        Returns the version of the GLib library
        :return: GLib library version string
        """
        return 'GLib {}.{}.{}'.format(
            glib_major_version, glib_minor_version, glib_micro_version)

    def supported_extensions(self):
        """
        Get the file extensions that are supported by the audio interface.
        Returns:
            A list of file extensions supported.
        """
        return ["wav", "ogg", "flac",]

    def get_master_volume(self):
        return round(self.audio_callback_data.master_volume / SDL_MIX_MAXVOLUME, 2)

    def set_master_volume(self, float volume):
        SDL_LockAudioDevice(self.audio_callback_data.device_id)
        self.audio_callback_data.master_volume = <Uint8>min(max(volume * SDL_MIX_MAXVOLUME, 0), SDL_MIX_MAXVOLUME)
        SDL_UnlockAudioDevice(self.audio_callback_data.device_id)

    def get_settings(self):
        """
        Gets the current audio interface settings. This method is only intended for testing purposes.
        Returns:
            A dictionary containing the current audio interface settings or None if the
            audio interface is not enabled.
        """
        if self.enabled:
            return {'sample_rate': self.audio_callback_data.sample_rate,
                    'audio_channels': self.audio_callback_data.channels,
                    'buffer_samples': self.audio_callback_data.buffer_samples,
                    'buffer_size': self.audio_callback_data.buffer_size
                    }
        else:
            return None

    cdef write_gst_log_message(self, message_type, message):
        """Write GStreamer log message to the mpfmc log"""
        # print(message_type, message)
        if message_type == 'error':
            self.log.error(message)
        elif message_type == 'warning':
            self.log.warning(message)
        elif message_type == 'info':
            self.log.info(message)

    @property
    def enabled(self):
        return SDL_GetAudioDeviceStatus(self.audio_callback_data.device_id) == SDL_AUDIO_PLAYING

    def enable(self):
        """
        Enables audio playback (begins audio processing)
        """
        self.log.debug("Enabling audio playback")

        SDL_PauseAudioDevice(self.audio_callback_data.device_id, 0)

    def disable(self):
        """
        Disables audio playback (stops audio processing)
        """
        self.log.debug("Disabling audio playback")
        self.stop_all_sounds()
        SDL_PauseAudioDevice(self.audio_callback_data.device_id, 1)

    def shutdown(self):
        """
        Shuts down the audio device
        """
        self.disable()
        Mix_CloseAudio()
        SDL_CloseAudioDevice(self.audio_callback_data.device_id)
        self.audio_callback_data.device_id = 0

    @staticmethod
    def get_max_tracks():
        """ Returns the maximum number of tracks allowed. """
        return MAX_TRACKS

    @staticmethod
    def get_max_markers():
        """Return the maximum number of markers allowed per sound"""
        return MAX_MARKERS

    def get_track_count(self):
        """ Returns the number of tracks that have been created. """
        return len(self.tracks)

    def get_track(self, int track_num):
        """
        Returns the track with the specified track number.
        Args:
            track_num: The track number to retrieve
        """
        try:
            return self.tracks[track_num]
        except IndexError:
            return None

    def get_track_by_name(self, str name not None):
        """
        Returns the track with the specified name.
        Args:
            name: The track name to retrieve
        """
        name = name.lower()
        for track in self.tracks:
            if name == track.name:
                return track

        return None

    def create_standard_track(self, object mc, str name not None,
                              int max_simultaneous_sounds=MAX_SIMULTANEOUS_SOUNDS_DEFAULT,
                              float volume=1.0):
        """
        Creates a new standard track in the audio interface
        Args:
            mc: The media controller app
            name: The name of the new track
            max_simultaneous_sounds: The maximum number of sounds that may be played at one time on the track
            volume: The track volume (0.0 to 1.0)

        Returns:
            A Track object for the newly created track
        """
        cdef int track_num = len(self.tracks)
        if track_num == MAX_TRACKS:
            self.log.error("Add track failed - the maximum number of tracks "
                           "(%d) has been reached.", MAX_TRACKS)
            return None

        # Make sure track name does not already exist (no duplicates allowed)
        name = name.lower()
        for track in self.tracks:
            if name == track.name:
                self.log.error("Add track failed - the track name '%s' already exists.", name)
                return None

        # Make sure audio callback function cannot be called while we are changing the track data
        SDL_LockAudioDevice(self.audio_callback_data.device_id)

        # Create the new standard track
        new_track = TrackStandard(mc,
                                  pycapsule.PyCapsule_New(&self.audio_callback_data, NULL, NULL),
                                  name,
                                  track_num,
                                  self.audio_callback_data.buffer_size,
                                  max_simultaneous_sounds,
                                  volume)
        self.tracks.append(new_track)

        # Update audio callback data with new track
        self.audio_callback_data.track_count = len(self.tracks)
        self.audio_callback_data.tracks[track_num] = new_track.state

        # Allow audio callback function to be called again
        SDL_UnlockAudioDevice(self.audio_callback_data.device_id)

        self.log.debug("The '%s' standard track has successfully been created.", name)

        return new_track

    def load_sound_file_to_memory(self, str file_name):
        """
        Loads an audio file into a SoundMemoryFile wrapper object for use in a Sound object.
        Used in asset loading for Sound objects.
        Args:
            file_name: The audio file name to load.

        Returns:
            A SoundMemoryFile wrapper object containing a pointer to the sound sample
            data in memory.  An exception is thrown if the sound is unable to be loaded.
        """
        return SoundMemoryFile(file_name, pycapsule.PyCapsule_New(&self.audio_callback_data, NULL, NULL))

    def load_sound_file_for_streaming(self, str file_name):
        """
        Loads an audio file into a SoundMemoryFile wrapper object for use in a Sound object.
        Used in asset loading for Sound objects.
        Args:
            file_name: The audio file name to load.

        Returns:
            A SoundMemoryFile wrapper object containing a pointer to the sound sample
            data in memory.  An exception is thrown if the sound is unable to be loaded.
        """
        return SoundStreamingFile(file_name, pycapsule.PyCapsule_New(&self.audio_callback_data, NULL, NULL))

    def unload_sound_file(self, container not None):
        """
        Unloads the source sample from the supplied container (used in Sound
        asset unloading).  The sound will no longer be in memory.
        Args:
            container: A SoundFile object
        """
        if not isinstance(container, SoundFile):
            return

        container.unload()


    def stop_sound(self, sound_instance not None):
        """
        Stops all instances of the specified sound immediately on all tracks.
        Args:
            sound_instance: The SoundInstance to stop
        """
        for track in self.tracks:
            track.stop_sound(sound_instance)

    def stop_all_sounds(self, float fade_out_seconds = 0.0):
        """Stops all playing and pending sounds in all tracks"""
        for track in self.tracks:
            track.stop_all_sounds(fade_out_seconds)

    def process(self):
        """Process tick function for the audio interface."""
        for track in self.tracks:
            track.process()

    @staticmethod
    cdef void audio_callback(void* data, Uint8 *output_buffer, int length) nogil:
        """
        Main audio callback function (called from SDL2).
        Args:
            data: A pointer to the AudioCallbackData class for the channel (contains all audio
                processing-related settings and state, ex: interface settings, tracks, sound
                players, ducking envelopes, etc.)
            output_buffer: A pointer to the audio data buffer for SDL2 to process
            length: The length of the audio buffer (in bytes)

        Notes:
            This static function is responsible for filling the supplied audio buffer with sound.
            samples. The function is called during the custom music player callback. Individual
            track buffers are maintained in each Track object and are processed during this callback.
        """
        cdef Uint32 buffer_length = <Uint32> length
        cdef AudioCallbackData *callback_data = <AudioCallbackData*> data
        cdef TrackState *track

        if callback_data == NULL:
            return

        # Initialize master output buffer with silence as it arrives uninitialized
        memset(output_buffer, 0, buffer_length)

        # Note: There are three separate loops over the tracks that must remain separate due
        # to various track parameters than can be set for any track during each loop.  Difficult
        # to debug logic errors will occur if these track loops are combined.

        # Loop over tracks, initializing the status, track buffer, and track ducking.
        for track_num in range(callback_data.track_count):

            callback_data.tracks[track_num].active = False
            memset(callback_data.tracks[track_num].buffer, 0, buffer_length)

            callback_data.tracks[track_num].ducking_is_active = False
            for control_point in range(CONTROL_POINTS_PER_BUFFER):
                callback_data.tracks[track_num].ducking_control_points[control_point] = SDL_MIX_MAXVOLUME

        # Loop over tracks, mixing the playing sounds into the track's audio buffer
        for track_num in range(callback_data.track_count):
            track = callback_data.tracks[track_num]

            # No need to process/mix the track if the track is stopped or paused
            if track.status == track_status_stopped or track.status == track_status_paused:
                continue

            # Call the track's mix function (based on track type)
            if track.type == track_type_standard:
                standard_track_mix_playing_sounds(track, buffer_length, callback_data)
            elif track.type == track_type_playlist:
                # TODO: Implement track mix function call
                pass
            elif track.type == track_type_live_loop:
                # TODO: Implement track mix function call
                pass

        # Loop over tracks again, applying ducking and mixing down tracks to the master output buffer
        for track_num in range(callback_data.track_count):

            # Only mix the track to the master output if it is active
            if callback_data.tracks[track_num].active:

                # Apply track ducking and volume and mix to output buffer
                mix_track_to_output(<TrackState*> callback_data.tracks[track_num],
                                    callback_data,
                                    output_buffer,
                                    buffer_length)

        # Apply master volume to output buffer
        SDL_MixAudioFormat(output_buffer, output_buffer, callback_data.format, buffer_length, callback_data.master_volume)

# ---------------------------------------------------------------------------
#    Global C functions designed to be called from the static audio callback
#    function (these functions do not use the GIL).
#
#    Note: Because these functions are only called from the audio callback
#    function, we do not need to lock and unlock the mutex in these functions
#    (locking/unlocking of the mutex is already performed in the audio
#    callback function.
# ---------------------------------------------------------------------------

cdef void standard_track_mix_playing_sounds(TrackState *track, Uint32 buffer_length, AudioCallbackData *callback_data) nogil:
    """
    Mixes any sounds that are playing on the specified standard track into the specified audio buffer.
    Args:
        track: A pointer to the TrackState data structure for the track
        buffer_length: The length of the output buffer (in bytes)
        callback_data: The audio callback data structure
    Notes:
        Notification messages are generated.
    """
    cdef TrackStandardState *standard_track
    cdef SoundPlayer *player
    cdef int player_num
    cdef int track_num
    cdef int marker_id
    cdef bint end_of_sound
    cdef bint ducking_is_active

    if track == NULL or track.type != track_type_standard:
        return

    standard_track = <TrackStandardState*>track.type_state

    # Setup local variables
    cdef Uint32 buffer_bytes_remaining
    cdef Uint32 current_chunk_bytes
    cdef Uint32 track_buffer_pos
    cdef Uint8 control_point
    cdef float progress

    # Loop over track sound players
    for player_num in range(standard_track.sound_player_count):

        player = cython.address(standard_track.sound_players[player_num])

        # If the player is idle, there is nothing to do so move on to the next player
        if player == NULL or player.status == player_idle:
            continue

        # Set flag indicating there is at least some activity on the track (it is active)
        track.active = True

        end_of_sound = False
        track_buffer_pos = 0
        control_point = 0
        buffer_bytes_remaining = buffer_length

        # Loop over output buffer at control rate
        while buffer_bytes_remaining > 0:

            # Determine the number of bytes to process in the current chunk
            current_chunk_bytes = min(buffer_bytes_remaining, callback_data.bytes_per_control_point)

            # Calculate volume of chunk (handle fading)
            if player.current.fading_status == fading_status_fading_in:
                volume = <Uint8> (in_out_quad((player.current.fade_in_steps - player.current.fade_steps_remaining) / player.current.fade_in_steps) * player.current.volume)
                player.current.fade_steps_remaining -= 1
                if player.current.fade_steps_remaining == 0:
                    player.current.fading_status = fading_status_not_fading
            elif player.current.fading_status == fading_status_fading_out:
                volume = <Uint8> (in_out_quad(player.current.fade_steps_remaining / player.current.fade_out_steps) * player.current.volume)
                player.current.fade_steps_remaining -= 1
            else:
                volume = player.current.volume

            # Copy samples for chunk to output buffer and apply volume
            if player.current.sample.type == sound_type_memory:
                end_of_sound = get_memory_sound_samples(cython.address(player.current), current_chunk_bytes, track.buffer + track_buffer_pos, volume, track, player_num)
            elif player.current.sample.type == sound_type_streaming:
                end_of_sound = get_streaming_sound_samples(cython.address(player.current), current_chunk_bytes, track.buffer + track_buffer_pos, volume, track, player_num)

            # Process sound ducking (if applicable)
            if player.current.sound_has_ducking:
                ducking_is_active = False

                # Determine control point ducking stage and calculate control point (test stages in reverse order)
                if player.current.sample_pos >= player.current.ducking_settings.release_start_pos + player.current.ducking_settings.release_duration:
                    # Ducking finished
                    player.current.ducking_control_points[control_point] = SDL_MIX_MAXVOLUME

                elif player.current.sample_pos >= player.current.ducking_settings.release_start_pos:
                    # Ducking release stage
                    ducking_is_active = True
                    progress = (player.current.sample_pos - player.current.ducking_settings.release_start_pos) / player.current.ducking_settings.release_duration
                    player.current.ducking_control_points[control_point] = \
                        lerpU8(in_out_quad(progress), player.current.ducking_settings.attenuation_volume, SDL_MIX_MAXVOLUME)

                elif player.current.sample_pos >= player.current.ducking_settings.attack_start_pos + player.current.ducking_settings.attack_duration:
                    # Ducking hold state
                    ducking_is_active = True
                    player.current.ducking_control_points[control_point] = player.current.ducking_settings.attenuation_volume

                elif player.current.sample_pos >= player.current.ducking_settings.attack_start_pos:
                    # Ducking attack stage
                    ducking_is_active = True
                    progress = (player.current.sample_pos - player.current.ducking_settings.attack_start_pos) / player.current.ducking_settings.attack_duration
                    player.current.ducking_control_points[control_point] = \
                        lerpU8(in_out_quad(progress), SDL_MIX_MAXVOLUME, player.current.ducking_settings.attenuation_volume)

                else:
                    # Ducking delay stage
                    player.current.ducking_control_points[control_point] = SDL_MIX_MAXVOLUME

                # Apply ducking to target track(s) (when applicable)
                if ducking_is_active:
                    for track_num in range(callback_data.track_count):
                        if (1 << track_num) & player.current.ducking_settings.track_bit_mask:
                            callback_data.tracks[track_num].ducking_is_active = True
                            callback_data.tracks[track_num].ducking_control_points[control_point] = min(
                                callback_data.tracks[track_num].ducking_control_points[control_point],
                                player.current.ducking_control_points[control_point])

                # TODO: Hold sound processing until ducking has finished
                # It is possible to have the ducking release finish after the sound has stopped.  In that
                # case, silence should be generated until the ducking is done.

            # Process markers (do any markers fall in the current chunk?)
            # Note: the current sample position has already been incremented when the sample data was received so
            # we need to look backwards from the current position to determine if marker falls in chunk window.
            for marker_id in range(player.current.marker_count):
                if player.current.sample_pos - current_chunk_bytes <= player.current.markers[marker_id] < player.current.sample_pos:
                    # Marker is in window, send notification
                    send_sound_marker_notification(player_num,
                                                   player.current.sound_id,
                                                   player.current.sound_instance_id,
                                                   track,
                                                   marker_id)
                # Special check if buffer wraps back around to the beginning of the sample
                if not end_of_sound and player.current.sample_pos - current_chunk_bytes < 0 and player.current.markers[marker_id] < player.current.sample_pos:
                    # Marker is in window, send notification
                    send_sound_marker_notification(player_num,
                                                   player.current.sound_id,
                                                   player.current.sound_instance_id,
                                                   track,
                                                   marker_id)

            # Check if sound is finished due to a fade out completing
            if player.current.fading_status == fading_status_fading_out and player.current.fade_steps_remaining == 0:
                end_of_sound = True

            # Sound finished processing
            if end_of_sound:
                send_sound_stopped_notification(player_num, player.current.sound_id, player.current.sound_instance_id, track)

                # End of sound behavior depends upon player status
                if player.status == player_replacing:
                    # Replacing the current sound with a new one: copy sound player settings from next sound to current
                    player.current.sample = player.next.sample
                    player.current.sample_pos = player.next.sample_pos
                    player.current.current_loop = player.next.current_loop
                    player.current.sound_id = player.next.sound_id
                    player.current.sound_instance_id = player.next.sound_instance_id
                    player.current.volume = player.next.volume
                    player.current.loops_remaining = player.next.loops_remaining
                    player.current.sound_priority = player.next.sound_priority
                    player.current.fade_in_steps = player.next.fade_in_steps
                    player.current.fade_out_steps = player.next.fade_out_steps
                    player.current.fade_steps_remaining = player.next.fade_steps_remaining
                    player.current.fading_status = player.next.fading_status
                    player.current.marker_count = player.next.marker_count

                    for marker_id in range(player.next.marker_count):
                        player.current.markers[marker_id] = player.next.markers[marker_id]

                    if player.next.sound_has_ducking:
                        player.current.sound_has_ducking = True
                        player.current.ducking_settings.track_bit_mask = player.next.ducking_settings.track_bit_mask
                        player.current.ducking_settings.attack_start_pos = player.next.ducking_settings.attack_start_pos
                        player.current.ducking_settings.attack_duration = player.next.ducking_settings.attack_duration
                        player.current.ducking_settings.attenuation_volume = player.next.ducking_settings.attenuation_volume
                        player.current.ducking_settings.release_start_pos = player.next.ducking_settings.release_start_pos
                        player.current.ducking_settings.release_duration = player.next.ducking_settings.release_duration
                    else:
                        player.current.sound_has_ducking = False

                    # Send sound started notification
                    send_sound_started_notification(player_num, player.current.sound_id, player.current.sound_instance_id, track)
                    player.status = player_playing
                    sound_finished = False
                else:
                    player.status = player_idle
                    break

            # Move to next chunk
            buffer_bytes_remaining -= current_chunk_bytes
            track_buffer_pos += current_chunk_bytes
            control_point += 1

cdef bint get_memory_sound_samples(SoundSettings *sound, Uint32 length, Uint8 *output_buffer, Uint8 volume,
                                   TrackState *track, int player_num) nogil:
    """
    Retrieves the specified number of bytes from the source sound memory buffer and mixes them into
    the track output buffer at the specified volume.

    Args:
        sound: A pointer to a SoundSettings struct (contains all sound state and settings to play the sound)
        length: The number of samples to retrieve and place in the output buffer
        output_buffer: The output buffer
        volume: The volume to apply to the output buffer (fixed for the duration of this method)
        track: A pointer to the TrackState struct for the current track
        player_num: The sound player number currently playing the sound (used for notification messages)

    Returns:
        True if sound is finished, False otherwise
    """
    if sound == NULL or output_buffer == NULL:
        return True

    cdef Uint32 samples_remaining_to_output = length
    cdef Uint32 samples_remaining_in_sound
    cdef Uint32 buffer_pos = 0
    cdef Uint8 *sound_buffer = <Uint8*>sound.sample.data.memory.data
    if sound_buffer == NULL:
        return True

    while samples_remaining_to_output > 0:

        # Determine how many samples are remaining in the sound buffer before the end of the sound
        samples_remaining_in_sound = sound.sample.data.memory.size - sound.sample_pos

        # Determine if we are consuming the entire remaining sound buffer, or just a portion of it
        if samples_remaining_to_output < samples_remaining_in_sound:
            # We are not consuming the entire streaming buffer.  There will still be buffer data remaining for the next call.
            SDL_MixAudioFormat(output_buffer + buffer_pos, <Uint8*>sound.sample.data.memory.data + sound.sample_pos, track.callback_data.format, samples_remaining_to_output, volume)

            # Update buffer position pointers
            sound.sample_pos += samples_remaining_to_output

            # Sound is not finished, but the output buffer has been filled
            return False
        else:
            # Entire sound buffer consumed. Mix in remaining samples
            SDL_MixAudioFormat(output_buffer + buffer_pos, <Uint8*>sound.sample.data.memory.data + sound.sample_pos, track.callback_data.format, samples_remaining_in_sound, volume)

            # Update buffer position pointers/samples remaining to place in the output buffer
            samples_remaining_to_output -= samples_remaining_in_sound
            sound.sample_pos += samples_remaining_in_sound
            buffer_pos += samples_remaining_in_sound

        # Check if we are at the end of the source sample buffer (loop if applicable)
        if sound.sample_pos >= sound.sample.data.memory.size:
            if sound.loops_remaining > 0:
                # At the end and still loops remaining, loop back to the beginning
                sound.loops_remaining -= 1
                sound.sample_pos = 0
                sound.current_loop += 1
                send_sound_looping_notification(player_num, sound.sound_id, sound.sound_instance_id, track)

            elif sound.loops_remaining == 0:
                # At the end and not looping, the sample has finished playing (return True for end of sound)
                return True

            else:
                # Looping infinitely, loop back to the beginning
                sound.sample_pos = 0
                sound.current_loop += 1
                send_sound_looping_notification(player_num, sound.sound_id, sound.sound_instance_id, track)

    return False

cdef bint get_streaming_sound_samples(SoundSettings *sound, Uint32 length, Uint8 *output_buffer, Uint8 volume,
                                      TrackState *track, int player_num) nogil:
    """
    Retrieves the specified number of bytes from the source sound streaming buffer and mixes them
    into the track output buffer at the specified volume.

    Args:
        sound: A pointer to a SoundSettings struct (contains all sound state and settings to play the sound)
        length: The number of samples to retrieve and place in the output buffer
        output_buffer: The output buffer
        volume: The volume to apply to the output buffer (fixed for the duration of this method)
        track: A pointer to the TrackState struct for the current track
        player_num: The sound player number currently playing the sound (used for notification messages)

    Returns:
        True if sound is finished, False otherwise

    Notes:
        The important thing to consider about retrieving samples from the streaming sound source
        is the buffer size used by SDL2 (output) and GStreamer (input) may be very different. A
        buffer is "pulled" synchronously from the streaming source and is held until it is
        completely consumed.  At which point either the sound ends if the source reports is at the
        end of stream (eos), or another buffer is pulled.
    """
    if sound == NULL or output_buffer == NULL or sound.sample.data.stream.pipeline == NULL:
        return True

    cdef Uint32 samples_remaining_to_output = length
    cdef Uint32 samples_remaining_in_map
    cdef Uint32 buffer_pos = 0

    while samples_remaining_to_output > 0:

        # Copy any samples remaining in the streaming buffer
        if sound.sample.data.stream.map_contains_valid_sample_data:
            samples_remaining_in_map = sound.sample.data.stream.map_info.size - sound.sample.data.stream.map_buffer_pos

            # Determine if we are consuming the entire buffer of streaming samples, or just a portion of it
            if samples_remaining_to_output < samples_remaining_in_map:
                # We are not consuming the entire streaming buffer.  There will still be buffer data remaining for the next call.
                SDL_MixAudioFormat(output_buffer + buffer_pos, sound.sample.data.stream.map_info.data + sound.sample.data.stream.map_buffer_pos, track.callback_data.format, samples_remaining_to_output, volume)

                # Update buffer position pointers
                sound.sample.data.stream.map_buffer_pos += samples_remaining_to_output
                sound.sample_pos += samples_remaining_to_output

                # Sound is not finished, but the output buffer has been filled
                return False
            else:
                # Entire buffer of leftover samples consumed.  Free the buffer resources to prepare for next call
                SDL_MixAudioFormat(output_buffer + buffer_pos, sound.sample.data.stream.map_info.data + sound.sample.data.stream.map_buffer_pos, track.callback_data.format, samples_remaining_in_map, volume)

                # Update buffer position pointers/samples remaining to place in the output buffer
                samples_remaining_to_output -= samples_remaining_in_map
                sound.sample_pos += samples_remaining_in_map
                buffer_pos += samples_remaining_in_map

                # Done with the streaming buffer, release references to it
                gst_buffer_unmap(sound.sample.data.stream.buffer, &sound.sample.data.stream.map_info)
                gst_sample_unref(sound.sample.data.stream.sample)

                sound.sample.data.stream.buffer = NULL
                sound.sample.data.stream.sample = NULL
                sound.sample.data.stream.map_buffer_pos = 0
                sound.sample.data.stream.map_contains_valid_sample_data = 0

        # Check for eos (end of stream)
        if g_object_get_bool(sound.sample.data.stream.sink, "eos"):

            # At the end of the stream - check if sound should loop or end
            if sound.loops_remaining > 0:
                # At the end and still loops remaining, loop back to the beginning
                sound.loops_remaining -= 1
                sound.sample_pos = 0
                sound.current_loop += 1
                send_sound_looping_notification(player_num, sound.sound_id, sound.sound_instance_id, track)

            elif sound.loops_remaining == 0:
                # At the end and not looping, the sample has finished playing (return True for end of sound)
                return True

            else:
                # Looping infinitely, loop back to the beginning
                sound.sample_pos = 0
                sound.current_loop += 1
                send_sound_looping_notification(player_num, sound.sound_id, sound.sound_instance_id, track)

            # Seek back to the beginning of the sound's source file
            gst_element_seek_simple(sound.sample.data.stream.pipeline, GST_FORMAT_TIME, <GstSeekFlags>(GST_SEEK_FLAG_FLUSH | GST_SEEK_FLAG_KEY_UNIT), 0)

        # Retrieve the next buffer from the streaming pipeline
        sound.sample.data.stream.sample = c_appsink_pull_sample(sound.sample.data.stream.sink)

        if sound.sample.data.stream.sample == NULL:
            sound.sample.data.stream.null_buffer_count += 1

            # If we've received too many consecutive null buffers, end the sound
            if sound.sample.data.stream.null_buffer_count > CONSECUTIVE_NULL_STREAMING_BUFFER_LIMIT:
                return True
        else:
            sound.sample.data.stream.null_buffer_count = 0
            sound.sample.data.stream.buffer = gst_sample_get_buffer(sound.sample.data.stream.sample)

            if gst_buffer_map(sound.sample.data.stream.buffer, &sound.sample.data.stream.map_info, GST_MAP_READ):
                sound.sample.data.stream.map_contains_valid_sample_data = 1
                sound.sample.data.stream.map_buffer_pos = 0
            else:
                sound.sample.data.stream.map_contains_valid_sample_data = 0
                sound.sample.data.stream.map_buffer_pos = 0
                gst_sample_unref(sound.sample.data.stream.sample)
                sound.sample.data.stream.sample = NULL

    # The sound has not finished playing, but the output buffer has been filled
    return False

cdef inline void end_of_sound_processing(SoundPlayer* player,
                                         TrackState *track) nogil:
    """
    Determines the action to take at the end of the sound (loop or stop) based on
    the current settings.  This function should be called when a sound processing
    loop has reached the end of the source buffer.
    Args:
        player: SoundPlayer pointer
        track: TrackState pointer for the current track
    """
    # Check if we are at the end of the source sample buffer (loop if applicable)
    if player.current.loops_remaining > 0:
        # At the end and still loops remaining, loop back to the beginning
        player.current.loops_remaining -= 1
        player.current.sample_pos = 0
        player.current.current_loop += 1
        send_sound_looping_notification(player.number,
                                 player.current.sound_id, player.current.sound_instance_id,
                                 track)

    elif player.current.loops_remaining == 0:
        # At the end and not looping, the sample has finished playing
        player.status = player_finished

    else:
        # Looping infinitely, loop back to the beginning
        player.current.sample_pos = 0
        player.current.current_loop += 1
        send_sound_looping_notification(player.number,
                                 player.current.sound_id, player.current.sound_instance_id,
                                 track)

cdef inline void send_sound_started_notification(int player, long sound_id, long sound_instance_id,
                                                 TrackState *track) nogil:
    """
    Sends a sound started notification
    Args:
        player: The sound player number on which the event occurred
        sound_id: The sound id
        sound_instance_id: The sound instance id
        track: The TrackState pointer
    """
    cdef NotificationMessageContainer *notification_message = _create_notification_message()
    if notification_message != NULL:
        notification_message.message = notification_sound_started
        notification_message.player = player
        notification_message.sound_id = sound_id
        notification_message.sound_instance_id = sound_instance_id

        track.notification_messages = g_slist_prepend(track.notification_messages, notification_message)

cdef inline void send_sound_stopped_notification(int player, long sound_id, long sound_instance_id,
                                                 TrackState *track) nogil:
    """
    Sends a sound stopped notification
    Args:
        player: The sound player number on which the event occurred
        sound_id: The sound id
        sound_instance_id: The sound instance id
        track: The TrackState pointer
    """
    cdef NotificationMessageContainer *notification_message = _create_notification_message()
    if notification_message != NULL:
        notification_message.message = notification_sound_stopped
        notification_message.player = player
        notification_message.sound_id = sound_id
        notification_message.sound_instance_id = sound_instance_id

        track.notification_messages = g_slist_prepend(track.notification_messages, notification_message)

cdef inline void send_sound_looping_notification(int player, long sound_id, long sound_instance_id,
                                                 TrackState *track) nogil:
    """
    Sends a sound looping notification
    Args:
        player: The sound player number on which the event occurred
        sound_id: The sound id
        sound_instance_id: The sound instance id
        track: The TrackState pointer
    """
    cdef NotificationMessageContainer *notification_message = _create_notification_message()
    if notification_message != NULL:
        notification_message.message = notification_sound_looping
        notification_message.player = player
        notification_message.sound_id = sound_id
        notification_message.sound_instance_id = sound_instance_id

        track.notification_messages = g_slist_prepend(track.notification_messages, notification_message)

cdef inline void send_sound_marker_notification(int player, long sound_id, long sound_instance_id,
                                                TrackState *track,
                                                int marker_id) nogil:
    """
    Sends a sound marker notification message
    Args:
        player: The sound player number on which the event occurred
        sound_id: The sound id
        sound_instance_id: The sound instance id
        track: The TrackState pointer
        marker_id: The id of the marker being sent for the specified sound
    """
    cdef NotificationMessageContainer *notification_message = _create_notification_message()
    if notification_message != NULL:
        notification_message.message = notification_sound_marker
        notification_message.player = player
        notification_message.sound_id = sound_id
        notification_message.sound_instance_id = sound_instance_id
        notification_message.data.marker.id = marker_id

        track.notification_messages = g_slist_prepend(track.notification_messages, notification_message)

cdef inline void send_track_stopped_notification(TrackState *track) nogil:
    """
    Sends a track stopped notification
    Args:
        track: The TrackState pointer
    """
    cdef NotificationMessageContainer *notification_message = _create_notification_message()
    if notification_message != NULL:
        notification_message.message = notification_track_stopped
        track.notification_messages = g_slist_prepend(track.notification_messages, notification_message)

cdef inline void send_track_paused_notification(TrackState *track) nogil:
    """
    Sends a track paused notification
    Args:
        track: The TrackState pointer
    """
    cdef NotificationMessageContainer *notification_message = _create_notification_message()
    if notification_message != NULL:
        notification_message.message = notification_track_paused
        track.notification_messages = g_slist_prepend(track.notification_messages, notification_message)

cdef inline Uint8 lerpU8(float progress, Uint8 a, Uint8 b) nogil:
    """
    Linearly interpolate between 2 8-bit values.
    Args:
        progress: Progress (0.0 to 1.0) between the two values
        a: First 8-bit value
        b: Second 8-bit value

    Returns:
        New 8-bit value between the supplied values
    """
    return <Uint8> ((1.0 - progress) * a + progress * b)

cdef inline float in_out_quad(float progress) nogil:
    """
    A quadratic easing function used for smoother audio fading
    Args:
        progress: 0.0 to 1.0

    Notes:
        At 0.0 the output is 0.0 and at 1.0 the output is 1.0.
    """
    cdef float p
    p = progress * 2
    if p < 1:
        return 0.5 * p * p
    p -= 1.0
    return -0.5 * (p * (p - 2.0) - 1.0)

cdef void mix_track_to_output(TrackState *track, AudioCallbackData* callback_data,
                              Uint8 *output_buffer, Uint32 buffer_length) nogil:
    """
    Applies ducking and mixes a track buffer into the master audio output buffer.
    Args:
        track: The track's state structure
        callback_data: The audio callback data structure
        output_buffer: The master audio output buffer.
        buffer_length: The audio buffer size to process.

    """

    cdef Uint8 *track_buffer
    cdef Uint32 output_buffer_bytes_remaining = buffer_length
    cdef Uint32 current_chunk_bytes
    cdef Uint32 buffer_pos = 0
    cdef Uint8 control_point = 0
    cdef Uint8 ducking_volume
    cdef Uint8 track_volume

    if track == NULL or track.status == track_status_stopped or track.status == track_status_paused:
        return

    track_buffer = <Uint8*>track.buffer

    # Loop over output buffer at control rate
    while output_buffer_bytes_remaining > 0:

        # Determine the number of bytes to process in the current chunk
        current_chunk_bytes = min(output_buffer_bytes_remaining, callback_data.bytes_per_control_point)

        # Apply any ducking to the track
        if track.ducking_is_active and control_point < CONTROL_POINTS_PER_BUFFER:
            ducking_volume = track.ducking_control_points[control_point]
        else:
            ducking_volume = SDL_MIX_MAXVOLUME

        # Calculate track volume (handle track fading)
        if track.fade_steps_remaining > 0:
            # Note: if the volume interpolation function below appears to be backwards, it is
            # because the fraction is going from 1 to 0 over the fade and not from a more
            # traditional 0 to 1.  This saves a few calculation cycles and is for efficiency.
            track.fade_volume_current = <Uint8> (lerpU8(in_out_quad(track.fade_steps_remaining / track.fade_steps),
                                                        track.fade_volume_target, track.fade_volume_start))
            track.fade_steps_remaining -= 1
        else:
            track.fade_volume_current = track.fade_volume_target
            if track.status == track_status_stopping:
                track.status = track_status_stopped
                send_track_stopped_notification(track)
            elif track.status == track_status_pausing:
                track.status = track_status_paused
                send_track_paused_notification(track)

        track_volume = ducking_volume * track.fade_volume_current // SDL_MIX_MAXVOLUME

        SDL_MixAudioFormat(output_buffer + buffer_pos, track_buffer + buffer_pos, callback_data.format, current_chunk_bytes, track_volume)

        output_buffer_bytes_remaining -= current_chunk_bytes
        buffer_pos += current_chunk_bytes
        control_point += 1

cdef inline NotificationMessageContainer *_create_notification_message() nogil:
    """
    Creates a new notification message.
    :return: A pointer to the new notification message.
    """
    return <NotificationMessageContainer*>g_slice_alloc0(sizeof(NotificationMessageContainer))


# ---------------------------------------------------------------------------
#    Track base class
# ---------------------------------------------------------------------------
cdef class Track:
    """
    Track base class
    """
    cdef dict _sound_instances_by_id
    cdef str _name
    cdef int _number
    cdef list _events_when_stopped
    cdef list _events_when_played
    cdef list _events_when_paused
    cdef object mc
    cdef SDL_AudioDeviceID device_id
    cdef object log

    # Track attributes need to be stored in a C struct in order for them to be accessible in
    # the SDL callback functions without the GIL (for performance reasons).  The TrackState
    # struct is allocated during construction and freed during destruction.
    cdef TrackState *state

    def __cinit__(self, *args, **kw):
        """C constructor"""
        self.state = NULL
        self.device_id = 0

    def __init__(self, object mc, object audio_callback_data, str name, int track_num, int buffer_size, float volume=1.0):
        """
        Constructor
        Args:
            mc: The media controller app
            audio_callback_data: The AudioCallbackData pointer wrapped in a PyCapsule object
            name: The track name
            track_num: The track number (corresponds to the SDL_Mixer channel number)
            buffer_size: The length of the track audio buffer in bytes
            volume: The track volume (0.0 to 1.0)
        """
        self.log = logging.getLogger("Track")
        self.mc = mc
        self._sound_instances_by_id = dict()
        self._name = name
        self._number = track_num
        self._events_when_stopped = None
        self._events_when_played = None
        self._events_when_paused = None

        # Allocate memory for the track state (common among all track types)
        self.state = <TrackState*> PyMem_Malloc(sizeof(TrackState))
        self.state.type = track_type_none
        self.state.type_state = NULL
        self.state.number = track_num
        self.state.buffer = <Uint8 *>PyMem_Malloc(buffer_size)
        self.state.buffer_size = buffer_size
        self.log.debug("Allocated track audio buffer (%d bytes)", buffer_size)

        # The easiest way to pass a C pointer in a constructor is to wrap it in a PyCapsule
        # (see https://docs.python.org/3.4/c-api/capsule.html).  This basically wraps the
        # pointer in a Python object. It can be extracted using PyCapsule_GetPointer.
        self.state.callback_data = <AudioCallbackData*>pycapsule.PyCapsule_GetPointer(audio_callback_data, NULL)
        self.device_id = self.state.callback_data.device_id

        self.state.status = track_status_playing
        self.state.fade_steps = 0
        self.state.fade_steps_remaining = 0
        new_volume = <Uint8>min(max(volume * SDL_MIX_MAXVOLUME, 0), SDL_MIX_MAXVOLUME)
        self.state.volume = new_volume
        self.state.fade_volume_current = new_volume
        self.state.fade_volume_start = new_volume
        self.state.fade_volume_target = new_volume

        self.state.notification_messages = NULL

    def __repr__(self):
        return '<Track.{}.{}>'.format(self.number, self.name)

    cdef TrackState *get_state(self):
        return self.state

    property name:
        def __get__(self):
            return self._name

    property volume:
        def __get__(self):
            return round(self.state.volume / SDL_MIX_MAXVOLUME, 2)

    @property
    def number(self):
        """Return the track number"""
        cdef int number = -1
        if self.state != NULL:
            SDL_LockAudioDevice(self.device_id)
            number = self.state.number
            SDL_UnlockAudioDevice(self.device_id)
        return number
    
    @property
    def events_when_stopped(self):
        """Return the list of events that are posted when the track is stopped"""
        return self._events_when_stopped
    
    @events_when_stopped.setter
    def events_when_stopped(self, events):
        """Sets the list of events that are posted when the track is stopped"""
        self._events_when_stopped = events

    @property
    def events_when_played(self):
        """Return the list of events that are posted when the track is played"""
        return self._events_when_played

    @events_when_played.setter
    def events_when_played(self, events):
        """Sets the list of events that are posted when the track is played"""
        self._events_when_played = events

    @property
    def events_when_paused(self):
        """Return the list of events that are posted when the track is paused"""
        return self._events_when_paused

    @events_when_paused.setter
    def events_when_paused(self, events):
        """Sets the list of events that are posted when the track is paused"""
        self._events_when_paused = events

    @property
    def supports_in_memory_sounds(self):
        """Return whether or not track supports in-memory sounds"""
        raise NotImplementedError('Must be overridden in derived class')

    @property
    def supports_streaming_sounds(self):
        """Return whether or not track supports streaming sounds"""
        raise NotImplementedError('Must be overridden in derived class')

    @property
    def fading(self):
        """Return whether or not the track is currently fading"""
        cdef bint fading = False
        if self.state != NULL:
            SDL_LockAudioDevice(self.device_id)
            fading = self.state.fade_steps_remaining > 0
            SDL_UnlockAudioDevice(self.device_id)
        return fading

    def set_volume(self, float volume, float fade_seconds = 0.0):
        """Sets the current track volume with an optional fade time"""
        cdef Uint8 new_volume = <Uint8>min(max(volume * SDL_MIX_MAXVOLUME, 0), SDL_MIX_MAXVOLUME)
        SDL_LockAudioDevice(self.device_id)

        # Fades require special logic
        if fade_seconds > 0:
            if self.state.status == track_status_stopping or self.state.status == track_status_pausing:
                # Fade is ignored if track is in the process of stopping or pausing
                self.state.volume = new_volume
            else:
                # If the track is currently in the middle of a fade, the existing fade
                # will be interrupted and a new fade will be calculated from the current
                # point of the existing fade
                if self.state.fade_steps_remaining > 0:
                    self.log.debug("set_volume - Interrupting an existing fade on this track so "
                                   "start a new fade")

                self.log.debug("set_volume - Applying %s second fade to new volume level", str(fade_seconds))

                # Calculate fade
                self.state.fade_steps = <Uint32>(fade_seconds * self.state.callback_data.seconds_to_bytes_factor) // self.state.callback_data.bytes_per_control_point
                self.state.fade_steps_remaining = self.state.fade_steps
                self.state.fade_volume_start = self.state.fade_volume_current
                self.state.fade_volume_target = new_volume
                self.state.volume = new_volume
        else:
            self.state.volume = new_volume
            self.state.fade_volume_current = new_volume
            self.state.fade_volume_start = new_volume
            self.state.fade_volume_target = new_volume

        SDL_UnlockAudioDevice(self.device_id)

    def play(self, float fade_in_seconds = 0.0):
        """
        Starts playing the track so it can begin processing sounds. Function has no effect if
        the track is already playing.
        Args:
            fade_in_seconds: The number of seconds to fade in the track
        """
        self.log.debug("play - Begin sound processing on track")

        SDL_LockAudioDevice(self.device_id)

        # Play is only supported when a track is paused, stopped, or is in the process of stopping
        if self.state.status == track_status_paused or \
                        self.state.status == track_status_stopped or \
                        self.state.status == track_status_stopping:
            if fade_in_seconds > 0:
                # Calculate fade data (steps and volume)
                self.log.debug("play - Applying %s second fade in", str(fade_in_seconds))
                self.state.fade_steps = <Uint32>(fade_in_seconds * self.state.callback_data.seconds_to_bytes_factor) // self.state.callback_data.bytes_per_control_point
                self.state.fade_steps_remaining = self.state.fade_steps
                self.state.fade_volume_start = self.state.fade_volume_current
                self.state.fade_volume_target = self.state.volume
            else:
                # No fade will occur, simply set volume
                self.state.fade_steps = 0
                self.state.fade_steps_remaining = 0
                self.state.fade_volume_current = self.state.volume
                self.state.fade_volume_start = self.state.volume
                self.state.fade_volume_target = self.state.volume

            self.state.status = track_status_playing

            # Trigger any events
            if self.events_when_played is not None:
                for event in self.events_when_played:
                    self.mc.post_mc_native_event(event)
        else:
            self.log.warning("play - Action may only be used when a track is stopped or is in the process "
                             "of stopping; action will be ignored.")

        SDL_UnlockAudioDevice(self.device_id)

    def stop(self, float fade_out_seconds = 0.0):
        """
        Stops the track and clears out any playing sounds. Function has no effect if the track is
        already stopped.
        Args:
            fade_out_seconds: The number of seconds to fade out the track
        """
        self.log.debug("stop - Stop sound processing on track and clear state")

        SDL_LockAudioDevice(self.device_id)

        # Stop is only supported when a track is playing
        if self.state.status in [track_status_playing, track_status_stopping, track_status_pausing]:

            if fade_out_seconds > 0:
                # Calculate fade data (steps and volume)
                self.log.debug("stop - Applying %s second fade out", str(fade_out_seconds))
                self.state.fade_steps = <Uint32>(fade_out_seconds * self.state.callback_data.seconds_to_bytes_factor) // self.state.callback_data.bytes_per_control_point
                self.state.fade_steps_remaining = self.state.fade_steps
                self.state.fade_volume_start = self.state.fade_volume_current
                self.state.fade_volume_target = 0
                self.state.status = track_status_stopping

            else:
                # No fade will occur, simply set volume
                self.state.fade_steps = 0
                self.state.fade_steps_remaining = 0
                self.state.fade_volume_current = 0
                self.state.fade_volume_start = 0
                self.state.fade_volume_target = 0
                self.state.status = track_status_stopped
                send_track_stopped_notification(self.state)

        else:
            self.log.warning("stop - Action may only be used when a track is playing; action "
                             "will be ignored.")

        SDL_UnlockAudioDevice(self.device_id)

    def pause(self, float fade_out_seconds = 0.0):
        """
        Pauses the track. Sounds will continue from where they left off when the track is resumed.
        Function has no effect unless the track is playing.
        Args:
            fade_out_seconds: The number of seconds to fade out the track
        """
        self.log.debug("pause - Pause sound processing on track")

        SDL_LockAudioDevice(self.device_id)

        # Stop is only supported when a track is playing
        if self.state.status in [track_status_playing, track_status_stopping, track_status_pausing]:
            if fade_out_seconds > 0:
                # Calculate fade data (steps and volume)
                self.log.debug("pause - Applying %s second fade out", str(fade_out_seconds))
                self.state.fade_steps = <Uint32>(fade_out_seconds * self.state.callback_data.seconds_to_bytes_factor) // self.state.callback_data.bytes_per_control_point
                self.state.fade_steps_remaining = self.state.fade_steps
                self.state.fade_volume_start = self.state.fade_volume_current
                self.state.fade_volume_target = 0
                self.state.status = track_status_pausing
            else:
                # No fade will occur, simply set volume
                self.state.fade_steps = 0
                self.state.fade_steps_remaining = 0
                self.state.fade_volume_current = 0
                self.state.fade_volume_start = 0
                self.state.fade_volume_target = 0
                self.state.status = track_status_paused
                send_track_paused_notification(self.state)

        else:
            self.log.warning("pause - Action may only be used when a track is playing; action "
                             "will be ignored.")

        SDL_UnlockAudioDevice(self.device_id)

    def process(self):
        """Processes the track queue each tick."""
        raise NotImplementedError('Must be overridden in derived class')


# ---------------------------------------------------------------------------
#    TrackStandard class
# ---------------------------------------------------------------------------
cdef class TrackStandard(Track):
    """
    Track class
    """
    # The name of the track
    cdef list _sound_queue
    cdef int _max_simultaneous_sounds

    # Track state needs to be stored in a C struct in order for them to be accessible in
    # the SDL callback functions without the GIL (for performance reasons).
    # The TrackStandardState struct is allocated during construction and freed during
    # destruction.
    cdef TrackStandardState *type_state

    def __init__(self, object mc, object audio_callback_data, str name, int track_num, int buffer_size,
                 int max_simultaneous_sounds=MAX_SIMULTANEOUS_SOUNDS_DEFAULT,
                 float volume=1.0):
        """
        Constructor
        Args:
            mc: The media controller app
            audio_callback_data: The AudioCallbackData struct wrapped in a PyCapsule
            name: The track name
            track_num: The track number
            buffer_size: The length of the track audio buffer in bytes
            max_simultaneous_sounds: The maximum number of sounds that can be played simultaneously
                on the track
            volume: The track volume (0.0 to 1.0)
        """
        # IMPORTANT: Call super class init function to allocate track state memory!
        super().__init__(mc, audio_callback_data, name, track_num, buffer_size, volume)

        self.log = logging.getLogger("Track." + str(track_num) + ".TrackStandard." + name)

        SDL_LockAudioDevice(self.device_id)

        self._sound_queue = list()

        # Set track type specific settings
        self.state.type = track_type_standard

        # Allocate memory for the specific track type state struct (TrackStandardState)
        self.type_state = <TrackStandardState*> PyMem_Malloc(sizeof(TrackStandardState))
        self.state.type_state = <void*>self.type_state

        # Make sure the number of simultaneous sounds is within the allowable range
        if max_simultaneous_sounds > MAX_SIMULTANEOUS_SOUNDS_LIMIT:
            self.log.warning("The maximum number of simultaneous sounds per track is %d",
                             MAX_SIMULTANEOUS_SOUNDS_LIMIT)
            max_simultaneous_sounds = MAX_SIMULTANEOUS_SOUNDS_LIMIT
        elif max_simultaneous_sounds < 1:
            self.log.warning("The minimum number of simultaneous sounds per track is 1")
            max_simultaneous_sounds = 1
        self._max_simultaneous_sounds = max_simultaneous_sounds
        self.type_state.sound_player_count = max_simultaneous_sounds

        # Allocate memory for the sound player structs needed for the desired number of
        # simultaneous sounds that can be played on the track.
        self.type_state.sound_players = <SoundPlayer*> PyMem_Malloc(self.type_state.sound_player_count * sizeof(SoundPlayer))

        # Initialize sound player attributes
        for i in range(self.type_state.sound_player_count):
            self.type_state.sound_players[i].status = player_idle
            self.type_state.sound_players[i].track_num = self.number
            self.type_state.sound_players[i].number = i
            self.type_state.sound_players[i].current.sample = NULL
            self.type_state.sound_players[i].current.loops_remaining = 0
            self.type_state.sound_players[i].current.current_loop = 0
            self.type_state.sound_players[i].current.volume = 0
            self.type_state.sound_players[i].current.sample_pos = 0
            self.type_state.sound_players[i].current.sound_id = 0
            self.type_state.sound_players[i].current.sound_instance_id = 0
            self.type_state.sound_players[i].current.sound_priority = 0
            self.type_state.sound_players[i].current.fading_status = fading_status_not_fading
            self.type_state.sound_players[i].current.almost_finished_marker = 0
            self.type_state.sound_players[i].current.sound_has_ducking = False
            self.type_state.sound_players[i].current.ducking_stage = ducking_stage_idle
            self.type_state.sound_players[i].next.sample = NULL
            self.type_state.sound_players[i].next.loops_remaining = 0
            self.type_state.sound_players[i].next.current_loop = 0
            self.type_state.sound_players[i].next.volume = 0
            self.type_state.sound_players[i].next.sample_pos = 0
            self.type_state.sound_players[i].next.sound_id = 0
            self.type_state.sound_players[i].next.sound_instance_id = 0
            self.type_state.sound_players[i].next.sound_priority = 0
            self.type_state.sound_players[i].next.fading_status = fading_status_not_fading
            self.type_state.sound_players[i].next.almost_finished_marker = 0
            self.type_state.sound_players[i].next.sound_has_ducking = False
            self.type_state.sound_players[i].next.ducking_stage = ducking_stage_idle

        self.log.debug("Created Track %d %s with the following settings: "
                       "simultaneous_sounds = %d, volume = %f",
                       self.number, self.name, self.max_simultaneous_sounds, self.volume)

        SDL_UnlockAudioDevice(self.device_id)

    def __dealloc__(self):
        """Destructor"""

        SDL_LockAudioDevice(self.device_id)

        # Free the specific track type state and other allocated memory
        if self.state != NULL:
            PyMem_Free(self.type_state.sound_players)
            PyMem_Free(self.type_state)
            self.state = NULL

        SDL_UnlockAudioDevice(self.device_id)

    def __repr__(self):
        return '<Track.{}.Standard.{}>'.format(self.number, self.name)

    @property
    def supports_in_memory_sounds(self):
        """Return whether or not track accepts in-memory sounds"""
        return True

    @property
    def supports_streaming_sounds(self):
        """Return whether or not track accepts streaming sounds"""
        return True

    @property
    def max_simultaneous_sounds(self):
        """Return the number of sounds that can be played simultaneously on this track"""
        return self._max_simultaneous_sounds

    cdef int _get_idle_sound_player(self):
        """
        Returns the index of the first idle sound player on the track.  If all
        players are currently busy playing, -1 is returned.
        """
        SDL_LockAudioDevice(self.device_id)

        for index in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[index].status == player_idle:
                SDL_UnlockAudioDevice(self.device_id)
                return index

        SDL_UnlockAudioDevice(self.device_id)
        return -1

    def process(self):
        """Processes the track queue each tick."""

        cdef bint keep_checking = True
        cdef int idle_sound_player
        cdef GSList *iterator = NULL

        # Lock the mutex to ensure no audio data is changed during the playback processing
        # (multi-threaded protection)
        SDL_LockAudioDevice(self.device_id)

        while keep_checking:
            # See if there are now any idle sound players
            idle_sound_player = self._get_idle_sound_player()
            if idle_sound_player >= 0:
                # Found an idle player, check if there are any sounds queued for playback
                sound_instance = self._get_next_sound()

                if sound_instance is not None:
                    self.log.debug("Getting sound from queue %s", sound_instance)
                    self._play_sound_on_sound_player(sound_instance=sound_instance, player=idle_sound_player)
                else:
                    keep_checking = False
            else:
                keep_checking = False

        # Process track notification messages
        if self.state.notification_messages != NULL:
            self.state.notification_messages = g_slist_reverse(self.state.notification_messages)
            iterator = self.state.notification_messages
            while iterator != NULL:
                self.process_notification_message(<NotificationMessageContainer*>iterator.data)
                g_slice_free1(sizeof(NotificationMessageContainer), iterator.data)
                iterator = iterator.next

            g_slist_free(self.state.notification_messages)
            self.state.notification_messages = NULL

        # Unlock the mutex since we are done accessing the audio data
        SDL_UnlockAudioDevice(self.device_id)

    cdef process_notification_message(self, NotificationMessageContainer *notification_message):
        """Process a notification message to this track"""

        if notification_message == NULL:
            return

        SDL_LockAudioDevice(self.device_id)

        # Check for track notification messages first (they do not need sound instance information)
        if notification_message.message in (notification_track_stopped, notification_track_paused):
            if notification_message.message == notification_track_stopped:
                self._reset_state()
                # Trigger any events
                if self.events_when_stopped is not None:
                    for event in self.events_when_stopped:
                        self.mc.post_mc_native_event(event)

            elif notification_message.message == notification_track_paused:
                # Trigger any events
                if self.events_when_paused is not None:
                    for event in self.events_when_paused:
                        self.mc.post_mc_native_event(event)
                pass

            SDL_UnlockAudioDevice(self.device_id)
            return

        self.log.debug("Processing notification message %d for sound instance (id: %d)",
                       notification_message.message, notification_message.sound_instance_id)

        if notification_message.sound_instance_id not in self._sound_instances_by_id:
            self.log.warning("Received a notification message for a sound instance (id: %d) "
                             "that is no longer managed in the audio library. "
                             "Notification will be discarded.",
                             notification_message.sound_instance_id)

        elif notification_message.message == notification_sound_started:
            sound_instance = self._sound_instances_by_id[notification_message.sound_instance_id]
            if sound_instance is not None:
                sound_instance.set_playing()

        elif notification_message.message == notification_sound_stopped:
            sound_instance = self._sound_instances_by_id[notification_message.sound_instance_id]
            if sound_instance is not None:
                sound_instance.set_stopped()
                self.log.debug("Removing sound instance %s from active sound dictionary", str(sound_instance))
                del self._sound_instances_by_id[sound_instance.id]

        elif notification_message.message == notification_sound_looping:
            sound_instance = self._sound_instances_by_id[notification_message.sound_instance_id]
            if sound_instance is not None:
                sound_instance.set_looping()

        elif notification_message.message == notification_sound_marker:
            sound_instance = self._sound_instances_by_id[notification_message.sound_instance_id]
            if sound_instance is not None:
                sound_instance.set_marker(notification_message.data.marker.id)
        else:
            raise AudioException("Unknown notification message received on %s track", self.name)

        SDL_UnlockAudioDevice(self.device_id)

    def _get_next_sound(self):
        """
        Returns the next sound in the priority queue ready for playback.

        Returns: A SoundInstance object. If the queue is empty, None is returned.

        This method ensures that the sound that is returned has not expired.
        If the next sound in the queue has expired, it is discarded and the
        next sound that has not expired is returned.
        """
        # We don't want to go through the entire sound queue more than once
        # in this method so keep track of the entry ids of the items we've
        # processed.  Once an item has been processed and retrieved again,
        # we are done and return None.
        cdef list sound_instances_retrieved_from_queue = list()
        while True:
            # Return none if sound queue is empty
            if len(self._sound_queue) == 0:
                return None

            # Get the next item in the queue (sorted by priority and expiration time)
            sound_instance = heappop(self._sound_queue)

            # Check if we've already processed the sound instance during this call (if
            # so, put it back in the queue and return)
            if sound_instance in sound_instances_retrieved_from_queue:
                heappush(self._sound_queue, sound_instance)
                return None

            # Keep track of entries we've processed during this call
            sound_instances_retrieved_from_queue.append(sound_instance)

            # If the sound is still loading and not expired, put it back in the queue
            if not sound_instance.sound.loaded and sound_instance.sound.loading and \
                    (sound_instance.exp_time is None or sound_instance.exp_time > time.time()):
                heappush(self._sound_queue, sound_instance)
                self.log.debug("Next pending sound in queue is still loading, "
                               "re-queueing sound %s",
                               sound_instance)
            else:
                # Return the next sound from the priority queue if it has not expired
                if sound_instance.exp_time is None or sound_instance.exp_time > time.time():
                    self.log.debug("Retrieving next pending sound from queue %s", sound_instance)
                    sound_instance.set_pending()  # Notify sound instance it is no longer queued
                    return sound_instance
                else:
                    self.log.debug("Discarding expired sound from queue %s", sound_instance)
                    sound_instance.set_expired()  # Notify sound instance it has expired

    def _remove_sound_from_queue(self, sound_instance not None):
        """
        Removes a sound from the priority sound queue.
        Args:
            sound_instance: The sound object to remove
        """
        try:
            self._sound_queue.remove(sound_instance)
            self.log.debug("Removing pending sound from queue %s", sound_instance)
            sound_instance.set_canceled()
            heapify(self._sound_queue)
        except ValueError:
            pass

    def _remove_all_sounds_from_queue(self):
        """Removes all sounds from the priority sound queue.
        """
        for sound_instance in self._sound_queue:
            self.log.debug("Removing pending sound from queue %s", sound_instance)
            sound_instance.set_canceled()

        self._sound_queue.clear()

    def play_sound(self, sound_instance not None):
        """
        Plays a sound on the current track.
        Args:
            sound_instance: The SoundInstance object to play
        """
        self.log.debug("play_sound - Processing sound '%s' for playback.", sound_instance.name)

        SDL_LockAudioDevice(self.device_id)

        # Sound instance cannot be played if the track is stopped or paused
        if self.state.status == track_status_stopped or self.state.status == track_status_paused:
            self.log.debug("play_sound - %s track is not currently playing and "
                           "therefore the request to play sound %s will be canceled",
                           self.name, sound_instance.name)
            sound_instance.set_canceled()
            SDL_UnlockAudioDevice(self.device_id)
            return

        if sound_instance.max_queue_time is None:
            sound_instance.exp_time = None
        else:
            sound_instance.exp_time = time.time() + sound_instance.max_queue_time

        # Make sure sound is loaded.  If not, we assume the sound is being loaded and we
        # add it to the queue so it will be picked up on the next loop.
        if not sound_instance.sound.loaded:
            # If the sound is not already loading, load it now
            if not sound_instance.sound.loading:
                sound_instance.sound.load()

            if sound_instance.max_queue_time != 0:
                self._queue_sound(sound_instance)
                self.log.debug("play_sound - Sound %s was not loaded and therefore has been "
                               "queued for playback.", sound_instance.name)
            else:
                self.log.debug("play_sound - Sound %s was not loaded and max_queue_time = 0, "
                               "therefore it has been discarded and will not be played.", sound_instance.name)
                sound_instance.set_expired()
        else:
            # If the sound can be played right away (available player) then play it.
            # Is there an available sound player?
            sound_player = self._get_sound_player_with_lowest_priority()
            player = sound_player[0]
            lowest_priority = sound_player[1]

            if lowest_priority is None:
                self.log.debug("play_sound - Sound player %d is available "
                               "for playback", player)
                # Play the sound using the available player
                self._play_sound_on_sound_player(sound_instance=sound_instance, player=player)
            else:
                # All sound players are currently busy:
                self.log.debug("play_sound - No idle sound player is available.")
                self.log.debug("play_sound - Sound player %d is currently playing the sound with "
                               "the lowest priority (%d).", player, lowest_priority)

                # If the lowest priority of all the sounds currently playing is lower than
                # the requested sound, kill the lowest priority sound and replace it.
                if sound_instance.priority > lowest_priority:
                    self.log.debug("play_sound - Sound priority (%d) is higher than the "
                                   "lowest sound currently playing (%d). Forcing playback "
                                   "on sound player %d.", sound_instance.priority, lowest_priority, player)
                    self._play_sound_on_sound_player(sound_instance=sound_instance,
                                                     player=player,
                                                     force=True)
                elif sound_instance.max_queue_time == 0:
                    # The sound could not be played immediately and has now expired (max_queue_time == 0)
                    self.log.debug("play_sound - Sound priority (%d) is less than or equal to the "
                                   "lowest sound currently playing (%d). Sound could not be played"
                                   "immediately and has now expired (max_queue_time = 0) and will "
                                   "not be played.",
                                   sound_instance.priority, lowest_priority)
                    sound_instance.set_expired()
                else:
                    # Add the requested sound to the priority queue
                    self.log.debug("play_sound - Sound priority (%d) is less than or equal to the "
                                   "lowest sound currently playing (%d). Sound will be queued "
                                   "for playback.", sound_instance.priority, lowest_priority)
                    self._queue_sound(sound_instance)

        SDL_UnlockAudioDevice(self.device_id)

    def replace_sound(self, old_instance not None, sound_instance not None):
        """
        Replace a currently playing instance with another sound instance.
        Args:
            old_instance: The currently playing sound instance to replace
            sound_instance: The new sound instance to begin playing immediately
        """

        self.log.debug("replace_sound - Preparing to replace existing sound with a new sound instance")

        # Find which player is currently playing the specified sound instance to replace
        SDL_LockAudioDevice(self.device_id)
        player = self._get_player_playing_sound_instance(old_instance)

        if player >= 0:
            self._play_sound_on_sound_player(sound_instance, player, force=True)
        else:
            self.log.debug("replace_sound - Could not locate specified sound instance to replace")
            sound_instance.set_canceled()

        SDL_UnlockAudioDevice(self.device_id)

    def _queue_sound(self, sound_instance not None):
        """Adds a sound to the queue to be played when a sound player becomes available.

        Args:
            sound_instance: The SoundInstance object to play.

        Note that this method will insert this sound into a position in the
        queue based on its priority, so highest-priority sounds are played
        first.
        """
        heappush(self._sound_queue, sound_instance)

        # Notify sound instance it has been queued
        sound_instance.set_queued()
        self.log.debug("Queueing sound %s", sound_instance)

    def stop_sound(self, sound_instance not None):
        """
        Stops all instances of the specified sound immediately on the track. Any queued instances
        will be removed from the queue.
        Args:
            sound_instance: The SoundInstance to stop
        """
        cdef SoundPlayer *player

        SDL_LockAudioDevice(self.device_id)

        self.log.debug("Stopping sound %s and removing any pending instances from queue", sound_instance.name)

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and self.type_state.sound_players[
                i].current.sound_instance_id == sound_instance.id:

                # Update player to stop playing sound
                player = cython.address(self.type_state.sound_players[i])

                # Calculate fade out (if necessary)
                player.current.fade_steps_remaining = sound_instance.fade_out * self.state.callback_data.seconds_to_bytes_factor // self.state.callback_data.bytes_per_control_point
                if player.current.fade_steps_remaining > 0:
                    player.current.fade_out_steps = player.current.fade_steps_remaining
                    player.current.fading_status = fading_status_fading_out
                    player.status = player_stopping
                else:
                    # Sound will stop immediately - send sound stopped notification
                    send_sound_stopped_notification(player.number, player.current.sound_id, player.current.sound_instance_id, self.state)
                    player.status = player_idle

                # Adjust ducking release (if necessary)
                if player.current.sound_has_ducking:
                    # player.current.ducking_settings.release_duration = min(sound_instance.ducking.release * self.state.callback_data.seconds_to_bytes_factor, request_message.data.stop.fade_out_duration)
                    # player.current.ducking_settings.release_start_pos = player.current.sample_pos
                    # TODO: Add more intelligent ducking release point calculation here:
                    #       Take into consideration whether ducking is already in progress and when it was
                    #       originally scheduled to finish.
                    pass

        # Remove any instances of the specified sound that are pending in the sound queue.
        if self.sound_instance_is_in_queue(sound_instance):
            self._remove_sound_from_queue(sound_instance)

        SDL_UnlockAudioDevice(self.device_id)

    def stop_sound_looping(self, sound_instance not None):
        """
        Stops all instances of the specified sound on the track after they finish the current loop.
        Any queued instances of the sound will be removed.
        Args:
            sound_instance: The Sound to stop
        """

        SDL_LockAudioDevice(self.device_id)

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and self.type_state.sound_players[
                i].current.sound_instance_id == sound_instance.id:
                # Set sound's loops_remaining variable to zero
                self.type_state.sound_players[i].current.loops_remaining = 0

        # Remove any instances of the specified sound that are pending in the sound queue.
        if self.sound_instance_is_in_queue(sound_instance):
            self._remove_sound_from_queue(sound_instance)

        SDL_UnlockAudioDevice(self.device_id)

    def _reset_state(self):
        """Resets the track state (stops all sounds immediately and clears the queue)"""
        SDL_LockAudioDevice(self.device_id)

        self.log.debug("Resetting track state (sounds will be stopped and queue cleared")

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle:
                # Set stop sound event
                send_sound_stopped_notification(i,
                                                self.type_state.sound_players[i].current.sound_id,
                                                self.type_state.sound_players[i].current.sound_instance_id,
                                                self.state)
                self.type_state.sound_players[i].status = player_idle

        # Remove all sounds that are pending in the sound queue.
        self._remove_all_sounds_from_queue()

        SDL_UnlockAudioDevice(self.device_id)

    def stop_all_sounds(self, float fade_out_seconds = 0.0):
        """
        Stops all playing sounds immediately on the track.
        Args:
            fade_out_seconds: The number of seconds to fade out the sounds before stopping
        """
        SDL_LockAudioDevice(self.device_id)

        self.log.debug("Stopping all sounds and removing any pending sounds from queue")

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle:

                # Update player to stop playing sound
                player = cython.address(self.type_state.sound_players[i])

                # Calculate fade out (if necessary)
                player.current.fade_steps_remaining = <Uint32>(fade_out_seconds * self.state.callback_data.seconds_to_bytes_factor // self.state.callback_data.bytes_per_control_point)
                if player.current.fade_steps_remaining > 0:
                    player.current.fade_out_steps = player.current.fade_steps_remaining
                    player.current.fading_status = fading_status_fading_out
                    player.status = player_stopping
                else:
                    # Sound will stop immediately - send sound stopped notification
                    send_sound_stopped_notification(player.number, player.current.sound_id, player.current.sound_instance_id, self.state)
                    player.status = player_idle

                # Adjust ducking release (if necessary)
                if player.current.sound_has_ducking:
                    # player.current.ducking_settings.release_duration = min(sound_instance.ducking.release * self.state.callback_data.seconds_to_bytes_factor, request_message.data.stop.fade_out_duration)
                    # player.current.ducking_settings.release_start_pos = player.current.sample_pos
                    # TODO: Add more intelligent ducking release point calculation here:
                    #       Take into consideration whether ducking is already in progress and when it was
                    #       originally scheduled to finish.
                    pass

        # Remove all sounds that are pending in the sound queue.
        self._remove_all_sounds_from_queue()

        SDL_UnlockAudioDevice(self.device_id)

    cdef tuple _get_sound_player_with_lowest_priority(self):
        """
        Retrieves the sound player currently with the lowest priority.

        Returns:
            A tuple consisting of the sound player index and the priority of
            the sound playing on that player (or None if the player is idle).

        """
        SDL_LockAudioDevice(self.device_id)

        cdef int lowest_priority = 2147483647
        cdef int sound_player = -1
        cdef int i

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status == player_idle:
                SDL_UnlockAudioDevice(self.device_id)
                return i, None
            elif self.type_state.sound_players[i].current.sound_priority < lowest_priority:
                lowest_priority = self.type_state.sound_players[i].current.sound_priority
                sound_player = i

        SDL_UnlockAudioDevice(self.device_id)
        return sound_player, lowest_priority

    cdef bint _play_sound_on_sound_player(self, sound_instance, int player, bint force=False):
        """
        Plays a sound using the specified sound player

        Args:
            sound_instance: The SoundInstance object to play
            player: The player number to use to play the sound
            force: Flag indicating whether or not the sound should be forced to play if
                the player is already busy playing another sound.

        Returns:
            True if sound instance was able to be played, False otherwise
        """
        self.log.debug("_play_sound_on_sound_player: %s, %s, %s", str(sound_instance), str(player), str(force))

        SDL_LockAudioDevice(self.device_id)

        # The sound cannot be played if the track is stopped or paused
        if self.state.status == track_status_stopped or self.state.status == track_status_paused:
            self.log.debug("_play_sound_on_sound_player - %s track is not currently playing and "
                           "therefore the request to play sound %s will be canceled",
                           self.name, sound_instance.name)
            sound_instance.set_canceled()
            SDL_UnlockAudioDevice(self.device_id)
            return False

        if not sound_instance.sound.loaded:
            self.log.debug("Specified sound is not loaded, could not "
                           "play sound %s", sound_instance.name)
            SDL_UnlockAudioDevice(self.device_id)
            return False

        # Make sure the player in range
        if player in range(self.type_state.sound_player_count):

            # If the specified sound player is not idle do not play the sound if force is not set
            if self.type_state.sound_players[player].status != player_idle and not force:
                self.log.debug("All sound players are currently in use, "
                               "could not play sound %s", sound_instance.name)
                SDL_UnlockAudioDevice(self.device_id)
                return False

            # Add sound to the dictionary of active sound instances
            self.log.debug("Adding sound instance %s to active sound dictionary", str(sound_instance))
            self._sound_instances_by_id[sound_instance.id] = sound_instance

            # Check if sound player is idle
            if self.type_state.sound_players[player].status == player_idle:
                # Start the player playing the sound instance
                self._set_player_playing(cython.address(self.type_state.sound_players[player]), sound_instance)
            else:
                # The player is currently busy playing another sound, force it to be replaced with the sound instance
                self._set_player_replacing(cython.address(self.type_state.sound_players[player]), sound_instance)

            self.log.debug("Sound %s is set to begin playback on playlist track (loops=%d)",
                           sound_instance.name, sound_instance.loops)

            SDL_UnlockAudioDevice(self.device_id)
            return True

        SDL_UnlockAudioDevice(self.device_id)
        return False

    cdef _set_player_sound_settings(self, SoundSettings *sound_settings, object sound_instance):
        """
        Set sound settings for the player from the sound instance.
        Args:
            sound_settings: A pointer to a SoundSettings structure
            sound_instance: The sound instance
        """
        if sound_settings == NULL or sound_instance is None:
            return

        # Get the sound sample buffer container
        cdef SoundFile sound_container = sound_instance.container

        # Setup the player to start playing the sound
        sound_settings.sample_pos = <Uint32>(sound_instance.start_at * self.state.callback_data.seconds_to_bytes_factor)
        sound_settings.current_loop = 0
        sound_settings.sound_id = sound_instance.sound.id
        sound_settings.sound_instance_id = sound_instance.id
        sound_settings.sample = cython.address(sound_container.sample)
        sound_settings.volume = <Uint8>(sound_instance.volume * SDL_MIX_MAXVOLUME)
        sound_settings.loops_remaining = sound_instance.loops
        sound_settings.sound_priority = sound_instance.priority

        # Fading (done at control rate; need to calculate the number of steps over which to fade in/out)
        sound_settings.fade_in_steps = sound_instance.fade_in * self.state.callback_data.seconds_to_bytes_factor // self.state.callback_data.bytes_per_control_point
        sound_settings.fade_out_steps = sound_instance.fade_out * self.state.callback_data.seconds_to_bytes_factor // self.state.callback_data.bytes_per_control_point
        sound_settings.fade_steps_remaining = sound_settings.fade_in_steps
        if sound_settings.fade_steps_remaining > 0:
            sound_settings.fading_status = fading_status_fading_in
        else:
            sound_settings.fading_status = fading_status_not_fading

        # Markers
        sound_settings.marker_count = sound_instance.marker_count
        if sound_instance.marker_count > 0:
            for index in range(sound_instance.marker_count):
                sound_settings.markers[index] = <Uint32>(sound_instance.markers[index]['time'] * self.state.callback_data.seconds_to_bytes_factor)

        # If the sound has ducking settings, apply them
        if sound_instance.ducking is not None and sound_instance.ducking.track_bit_mask != 0:
            # To convert between the number of seconds and a buffer position (bytes), we need to
            # account for the sample rate (sampes per second), the number of audio channels, and the
            # number of bytes per sample (all samples are 16 bits)
            sound_settings.sound_has_ducking = True
            sound_settings.ducking_settings.track_bit_mask = sound_instance.ducking.track_bit_mask
            sound_settings.ducking_settings.attack_start_pos = sound_instance.ducking.delay * self.state.callback_data.seconds_to_bytes_factor
            sound_settings.ducking_settings.attack_duration = sound_instance.ducking.attack * self.state.callback_data.seconds_to_bytes_factor
            sound_settings.ducking_settings.attenuation_volume = <Uint8>(sound_instance.ducking.attenuation * SDL_MIX_MAXVOLUME)
            sound_settings.ducking_settings.release_start_pos = sound_instance.ducking.release_point * self.state.callback_data.seconds_to_bytes_factor
            sound_settings.ducking_settings.release_duration = sound_instance.ducking.release * self.state.callback_data.seconds_to_bytes_factor
            sound_settings.ducking_stage = ducking_stage_delay
        else:
            sound_settings.sound_has_ducking = False

        # Special handling is needed to start streaming for the specified sound at the correct location
        if sound_container.sample.type == sound_type_streaming:
            # Seek to the specified start position
            gst_element_seek_simple(sound_container.sample.data.stream.pipeline,
                                    GST_FORMAT_TIME,
                                    <GstSeekFlags>(GST_SEEK_FLAG_FLUSH | GST_SEEK_FLAG_KEY_UNIT),
                                    sound_instance.start_at * GST_SECOND)
            with nogil:
                ret = gst_element_set_state(sound_container.sample.data.stream.pipeline, GST_STATE_PLAYING)

    cdef _set_player_playing(self, SoundPlayer *player, object sound_instance):
        """
        Sets the player status and sound settings to begin playing the sound instance
        Args:
            player: A pointer to the SoundPlayer on which to play the sound
            sound_instance: The sound instance to begin playing
        """
        if player == NULL or sound_instance is None:
            return

        # Setup the player to start playing the sound
        player.status = player_playing
        self._set_player_sound_settings(cython.address(player.current), sound_instance)

        # Send sound started notification
        send_sound_started_notification(player.number, player.current.sound_id, player.current.sound_instance_id, self.state)

        self.log.debug("Sound %s is set to begin playback on playlist track (loops=%d)",
                       sound_instance.name, sound_instance.loops)

    cdef _set_player_replacing(self, SoundPlayer *player, object sound_instance):
        """
        Sets the player status and sound settings to replace the currently playing sound with the
        sound instance.
        Args:
            player: A pointer to the SoundPlayer on which to replace the sound
            sound_instance: The sound instance to begin playing
        """
        if player == NULL or sound_instance is None:
            return

        # Set current sound to fade out quickly
        player.current.fade_out_steps = self.state.callback_data.quick_fade_steps
        player.current.fade_steps_remaining = self.state.callback_data.quick_fade_steps
        player.current.fading_status = fading_status_fading_out

        # Set the next sound to play immediately after the current one fades out
        player.status = player_replacing
        self._set_player_sound_settings(cython.address(player.next), sound_instance)

        # TODO: Figure out how to handle ducking when replacing an existing sound

    cdef int _get_player_playing_sound_instance(self, sound_instance):
        """
        Return the player currently playing the specified sound instance
        Args:
            sound_instance: The SoundInstance to find

        Returns:
            The sound player number currently playing the specified sound instance or -1 if the
            sound instance is not currently playing.
        """
        SDL_LockAudioDevice(self.device_id)

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and \
                            self.type_state.sound_players[i].current.sound_instance_id == sound_instance.id:
                SDL_UnlockAudioDevice(self.device_id)
                return i

        SDL_UnlockAudioDevice(self.device_id)
        return -1

    def get_status(self):
        """
        Get the current track status (status of all sound players on the track).
        Used for debugging and testing.
        Returns:
            A list of status dictionaries containing the current settings for each
            sound player.
        """
        SDL_LockAudioDevice(self.device_id)
        status = []
        for player in range(self.type_state.sound_player_count):
            status.append({
                "player": player,
                "status": TrackStandard.player_status_to_text(<int>self.type_state.sound_players[player].status),
                "fading_status": TrackStandard.player_fading_status_to_text(<int>self.type_state.sound_players[player].current.fading_status),
                "volume": self.type_state.sound_players[player].current.volume,
                "sound_id": self.type_state.sound_players[player].current.sound_id,
                "sound_instance_id": self.type_state.sound_players[player].current.sound_instance_id,
                "priority": self.type_state.sound_players[player].current.sound_priority,
                "loops": self.type_state.sound_players[player].current.loops_remaining,
                "has_ducking": self.type_state.sound_players[player].current.sound_has_ducking,
                "sample_pos": self.type_state.sound_players[player].current.sample_pos
            })

            self.log.debug("Status - Player %d: Status=%s, Sound=%d, SoundInstance=%d"
                           "Priority=%d, Loops=%d, SamplePos=%d",
                           player,
                           TrackStandard.player_status_to_text(
                               self.type_state.sound_players[player].status),
                           self.type_state.sound_players[player].current.sound_id,
                           self.type_state.sound_players[player].current.sound_instance_id,
                           self.type_state.sound_players[player].current.sound_priority,
                           self.type_state.sound_players[player].current.loops_remaining,
                           self.type_state.sound_players[player].current.sample_pos)

        SDL_UnlockAudioDevice(self.device_id)

        return status

    def get_sound_queue_count(self):
        """
        Gets the number of sounds currently in the track sound queue.
        Returns:
            Integer number of sounds currently in the track sound queue.
        """
        return len(self._sound_queue)

    def get_sound_players_in_use_count(self):
        """
        Gets the current count of sound players in use on the track.  Used for
        debugging and testing.
        Returns:
            Integer number of sound players currently in use on the track.
        """
        players_in_use_count = 0
        SDL_LockAudioDevice(self.device_id)
        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle:
                players_in_use_count += 1
        SDL_UnlockAudioDevice(self.device_id)
        return players_in_use_count

    def sound_is_playing(self, sound not None):
        """Returns whether or not the specified sound is currently playing on the track"""
        SDL_LockAudioDevice(self.device_id)
        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and \
                            self.type_state.sound_players[i].current.sound_id == sound.id:
                SDL_UnlockAudioDevice(self.device_id)
                return True

        SDL_UnlockAudioDevice(self.device_id)
        return False

    def sound_instance_is_playing(self, sound_instance not None):
        """Returns whether or not the specified sound instance is currently playing on the track"""
        SDL_LockAudioDevice(self.device_id)
        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and \
                            self.type_state.sound_players[i].current.sound_instance_id == sound_instance.id:
                SDL_UnlockAudioDevice(self.device_id)
                return True

        SDL_UnlockAudioDevice(self.device_id)
        return False

    def sound_is_in_queue(self, sound not None):
        """Returns whether or not an instance of the specified sound is currently in the queue"""
        for sound_instance in self._sound_queue:
            if sound_instance.sound.id == sound.id:
                return True

        return False

    def sound_instance_is_in_queue(self, sound_instance not None):
        """Returns whether or not the specified sound instance is currently in the queue"""
        return sound_instance in self._sound_queue

    @staticmethod
    def player_status_to_text(int status):
        """
        Converts a sound player status value into an equivalent text string.  Used for testing
        purposes only.
        Args:
            status: Integer sound player status value

        Returns:
            string containing the equivalent status text
        """
        status_values = {
            player_idle: "idle",
            player_pending: "pending",
            player_replacing: "replacing",
            player_playing: "playing",
            player_finished: "finished",
            player_stopping: "stopping",
        }

        try:
            return status_values.get(status)
        except KeyError:
            return "unknown"

    @staticmethod
    def player_fading_status_to_text(int fading_status):
        """
        Converts a sound player fading status value into an equivalent text string.  Used for
        testing purposes only.
        Args:
            fading_status: Integer sound player fading status value

        Returns:
            string containing the equivalent fading status text
        """
        fading_status_values = {
            fading_status_not_fading: "not fading",
            fading_status_fading_in: "fade in",
            fading_status_fading_out: "fade out",
        }

        try:
            return fading_status_values.get(fading_status)
        except KeyError:
            return "unknown"


# ---------------------------------------------------------------------------
#    SoundFile class
# ---------------------------------------------------------------------------
cdef class SoundFile:
    """SoundFile is the base class for wrapper classes used to manage sound sample data."""
    cdef str file_name
    cdef AudioCallbackData *callback_data
    cdef SoundSample sample
    cdef object log

    def __init__(self, str file_name, object audio_callback_data):
        self.log = logging.getLogger("SoundFile")
        self.file_name = file_name
        self.callback_data = <AudioCallbackData*>pycapsule.PyCapsule_GetPointer(audio_callback_data, NULL)
        self.sample.duration = 0

    def __repr__(self):
        return '<SoundFile>'

    def load(self):
        """Load the sound file"""
        raise NotImplementedError("Must be implemented in derived class")

    def unload(self):
        """Unload the sound file"""
        raise NotImplementedError("Must be implemented in derived class")

    @property
    def duration(self):
        """Return the duration of the sound file"""
        return self.sample.duration


# ---------------------------------------------------------------------------
#    SoundMemoryFile class
# ---------------------------------------------------------------------------
cdef class SoundMemoryFile(SoundFile):
    """SoundMemoryFile is a wrapper class to manage sound sample data stored
    in memory."""
    cdef bint _loaded_using_sdl

    def __init__(self, str file_name, object audio_callback_data):
        # IMPORTANT: Call super class init function
        super().__init__(file_name, audio_callback_data)
        self.log = logging.getLogger("SoundMemoryFile")
        self.sample.type = sound_type_memory
        self.sample.data.memory = <SampleMemory*>PyMem_Malloc(sizeof(SampleMemory))
        self.sample.data.memory.data = NULL
        self.sample.data.memory.size = 0

        self.load()

    def __dealloc__(self):
        self.unload()
        if self.sample.data.memory != NULL:
            PyMem_Free(self.sample.data.memory)

    def __repr__(self):
        if self.loaded:
            return '<SoundMemoryFile({}, Loaded=True, sample_duration={}s)>'.format(self.file_name, self.sample.duration)
        else:
            return "<SoundMemoryFile({}, Loaded=False)>".format(self.file_name)

    def load(self):
        """Loads the sound into memory using the most appropriate library for the format."""
        cdef Mix_Chunk *chunk

        if self.loaded:
            return

        if not os.path.isfile(self.file_name):
            raise AudioException('Could not locate file ' + self.file_name)

        # Load the audio file (will be converted to current sample output format)
        chunk = Mix_LoadWAV(self.file_name.encode('utf-8'))
        if chunk == NULL:
            msg = "Could not load sound file {} due to an error: {}".format(self.file_name, SDL_GetError())
            raise AudioException(msg)

        # Save the loaded sample data
        self.sample.data.memory.size = <gsize>chunk.alen
        self.sample.data.memory.data = <gpointer>chunk.abuf

        # Set the sample duration (in seconds)
        self.sample.duration = self.sample.data.memory.size / self.callback_data.seconds_to_bytes_factor

        # Free the chunk (sample memory will not be freed).  The chunk was allocated using SDL_malloc in the
        # SDL_Mixer library.  We do not want to use Mix_Free or the sample data will be freed.  Instead, we
        # can just free the Mix_Chunk structure using SDL_free and the sample buffer will remain intact. The
        # sample memory must be freed later when this object is deallocated.
        SDL_free(chunk)

        self.log.debug('Loaded file: %s Sample duration: %s',
                       self.file_name, self.sample.duration)

    def unload(self):
        """Unloads the sample data from memory"""
        if self.sample.data.memory.data != NULL:
            SDL_free(<void*>self.sample.data.memory.data)

        self.sample.data.memory.data = NULL
        self.sample.data.memory.size = 0

    @property
    def loaded(self):
        """Returns whether or not the sound file data is loaded in memory"""
        return self.sample.data.memory.data != NULL and self.sample.data.memory.size > 0


# ---------------------------------------------------------------------------
#    SoundStreamingFile class
# ---------------------------------------------------------------------------
cdef class SoundStreamingFile(SoundFile):
    """SoundStreamingFile is a wrapper class to manage streaming sound sample data."""
    cdef GstElement *pipeline
    cdef GstElement *source
    cdef GstElement *convert
    cdef GstElement *resample
    cdef GstElement *sink
    cdef GstBus *bus
    cdef gulong bus_message_handler_id

    def __cinit__(self, *args, **kwargs):
        """C constructor"""
        self.pipeline = NULL
        self.bus = NULL
        self.bus_message_handler_id = 0

    def __init__(self, str file_name, object audio_callback_data):
        # IMPORTANT: Call super class init function
        super().__init__(file_name, audio_callback_data)
        self.log = logging.getLogger("SoundStreamingFile")

        self.sample.type = sound_type_streaming
        self.sample.data.stream = <SampleStream*>PyMem_Malloc(sizeof(SampleStream))
        self.sample.data.stream.pipeline = NULL
        self.sample.data.stream.sink = NULL
        self.sample.data.stream.sample = NULL
        self.sample.data.stream.buffer = NULL
        self.sample.data.stream.map_contains_valid_sample_data = 0
        self.sample.data.stream.map_buffer_pos = 0
        self.sample.data.stream.null_buffer_count = 0

        self.load()

    def __dealloc__(self):
        if self.sample.data.stream != NULL:
            PyMem_Free(self.sample.data.stream)

    def __repr__(self):
        if self.loaded:
            return '<SoundStreamingFile({}, Loaded=True, sample_duration={}s)>'.format(self.file_name,self.sample.duration)
        return "<SoundStreamingFile({}, Loaded=False)>".format(self.file_name)

    def _gst_init(self):
        if gst_is_initialized():
            return True
        cdef int argc = 0
        cdef char **argv = NULL
        cdef GError *error
        if not gst_init_check(&argc, &argv, &error):
            msg = 'Unable to initialize gstreamer: code={} message={}'.format(
                    error.code, <bytes>error.message)
            raise AudioException(msg)

    def _destroy_pipeline(self):
        """Destroys the GStreamer pipeline"""
        """Destroys the current pipeline"""
        cdef GstState current_state, pending_state

        if self.bus != NULL and self.bus_message_handler_id != 0:
            c_signal_disconnect(<GstElement*>self.bus, self.bus_message_handler_id)
            self.bus_message_handler_id = 0

        if self.pipeline != NULL:
            # the state changes are async. if we want to guarantee that the
            # state is set to NULL, we need to query it. We also put a 5s
            # timeout for safety, but normally, nobody should hit it.
            with nogil:
                gst_element_set_state(self.pipeline, GST_STATE_NULL)
                gst_element_get_state(self.pipeline, &current_state,
                        &pending_state, <GstClockTime>5e9)
            gst_object_unref(self.pipeline)

        if self.bus != NULL:
            gst_object_unref(self.bus)

        self.bus = NULL
        self.pipeline = NULL

    def _construct_pipeline(self):
        """Creates the GStreamer pipeline used to stream the sound data"""
        cdef GError *error
        cdef GstSample *sample
        cdef gint64 duration = 0

        # Pipeline structure: uridecodebin --> audioconvert --> audioresample --> appsink

        # If the pipeline has already been created, delete it
        if self.pipeline != NULL:
            self._destroy_pipeline()

        # Pipeline structure: uridecodebin --> audioconvert --> audioresample --> appsink

        # Create GStreamer pipeline with the specified caps (from a string)
        file_path = 'file:///' + self.file_name.replace('\\', '/')
        if SDL_AUDIO_ISLITTLEENDIAN(self.callback_data.format):
            audio_format = "S16LE"
        else:
            audio_format = "S16BE"
        pipeline_string = 'uridecodebin uri="{}" ! audioconvert ! audioresample ! appsink name=sink caps="audio/x-raw,rate={},channels={},format={},layout=interleaved" sync=true blocksize={}'.format(
            file_path, str(self.callback_data.sample_rate), str(self.callback_data.channels), audio_format, self.callback_data.buffer_size)

        error = NULL
        self.pipeline = gst_parse_launch(pipeline_string.encode('utf-8'), &error)

        if error != NULL:
            msg = 'Unable to create a GStreamer pipeline: code={} message={}'.format(error.code, <bytes>error.message)
            raise AudioException(msg)

        # Get the pipeline bus (the bus allows applications to receive pipeline messages)
        self.bus = gst_pipeline_get_bus(<GstPipeline*>self.pipeline)
        if self.bus == NULL:
            raise AudioException('Unable to get bus from the pipeline')

        # Enable pipeline messages and callback message handler
        #gst_bus_enable_sync_message_emission(self.bus)
        #self.bus_message_handler_id = c_bus_connect_message(self.bus, _on_gst_bus_message, <void*>self.audio_interface)

        # Get sink
        self.sink = gst_bin_get_by_name(<GstBin*>self.pipeline, "sink")

        # Set to PAUSED to make the first frame arrive in the sink
        ret = gst_element_set_state(self.pipeline, GST_STATE_PAUSED)

        # Get the preroll sample (forces the code to wait until the sample has been completely loaded
        # which is necessary to retrieve the duration).
        sample = c_appsink_pull_preroll(self.sink)
        if sample != NULL:
            gst_sample_unref(sample)

        # Get duration of audio file (in nanoseconds)
        if not gst_element_query_duration(self.sink, GST_FORMAT_TIME, &duration):
            duration = 0

        # Store duration in seconds
        self.sample.duration = duration / GST_SECOND

        # The pipeline should now be ready to play.  Store the pointers to the pipeline
        # and appsink in the SampleStream struct for use in the application.
        self.sample.data.stream.pipeline = self.pipeline
        self.sample.data.stream.sink = self.sink

    def load(self):
        """Loads the sound into memory using GStreamer"""

        #if self.loaded:
        #    return

        self._gst_init()
        self._construct_pipeline()

        self.log.debug('Loaded file: %s Sample duration: %s',
                       self.file_name, self.sample.duration)

    def unload(self):
        """Unloads the sample data from memory"""

        # Done with the streaming buffer, release references to it
        if self.sample.data.stream.map_contains_valid_sample_data:
            gst_buffer_unmap(self.sample.data.stream.buffer, &self.sample.data.stream.map_info)
            gst_sample_unref(self.sample.data.stream.sample)

            self.sample.data.stream.buffer = NULL
            self.sample.data.stream.sample = NULL
            self.sample.data.stream.map_buffer_pos = 0
            self.sample.data.stream.map_contains_valid_sample_data = 0

        # Cleanup the streaming pipeline
        gst_element_set_state(self.pipeline, GST_STATE_NULL)
        gst_object_unref(self.pipeline)

    @property
    def loaded(self):
        """Returns whether or not the sound file data is loaded in memory"""
        return self.sample.data.stream != NULL and self.sample.data.stream.pipeline != NULL and self.sample.data.stream.sink != NULL

