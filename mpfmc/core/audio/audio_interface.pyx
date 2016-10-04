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

__version_info__ = ('0', '32', '0-dev11')
__version__ = '.'.join(__version_info__)

from libc.stdio cimport FILE, fopen, fprintf
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
DEF MAX_REQUEST_MESSAGES = 32
DEF MAX_NOTIFICATION_MESSAGES = 32
DEF QUICK_FADE_DURATION_SECS = 0.05
DEF BYTES_PER_SAMPLE = 2

DEF MAX_AUDIO_VALUE_S16 = ((1 << (16 - 1)) - 1)
DEF MIN_AUDIO_VALUE_S16 = -(1 << (16 - 1))


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

cdef void _on_gst_bus_message(void *userdata, GstMessage *message) with gil:
    cdef AudioInterface interface = <AudioInterface>userdata
    cdef GError *err = NULL
    if message.type == GST_MESSAGE_EOS:
        pass
    elif message.type == GST_MESSAGE_ERROR:
        gst_message_parse_error(message, &err, NULL)
        interface.write_gst_log_message('error', err.message)
        g_error_free(err)
    elif message.type == GST_MESSAGE_WARNING:
        gst_message_parse_warning(message, &err, NULL)
        interface.write_gst_log_message('warning', err.message)
        g_error_free(err)
    elif message.type == GST_MESSAGE_INFO:
        gst_message_parse_info(message, &err, NULL)
        interface.write_gst_log_message('info', err.message)
        g_error_free(err)
    else:
        pass


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
        cdef SDL_AudioSpec desired, obtained
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

        # Initialize GStreamer
        self._initialize_gstreamer()

        self.log.info("Initialized %s", AudioInterface.get_version())
        self.log.debug("Loaded %s", AudioInterface.get_sdl_version())
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
        self.disable()

        # Remove tracks
        self.tracks.clear()

        PyMem_Free(self.audio_callback_data.tracks)

        # SDL no longer needed
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
    def get_version(cls):
        """
        Retrieves the current version of the audio interface library
        :return: Audio interface library version string
        """
        return __version__

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
        return ["wav", "ogg", "flac", "m4a", "aiff"]

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

    def write_gst_log_message(self, message_type, message):
        """Write GStreamer log message to the mpfmc log"""
        print(message_type, message)
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

    def create_live_loop_track(self, object mc, str name not None, float volume=1.0):
        """
        Creates a new live loop track in the audio interface
        Args:
            mc: The media controller app
            name: The name of the new track
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

        # Create the new live loop track
        new_track = TrackLiveLoop(mc,
                                  pycapsule.PyCapsule_New(&self.audio_callback_data, NULL, NULL),
                                  name,
                                  track_num,
                                  self.audio_callback_data.buffer_size,
                                  volume)
        self.tracks.append(new_track)

        # Update audio callback data with new track
        self.audio_callback_data.track_count = len(self.tracks)
        self.audio_callback_data.tracks[track_num] = new_track.state

        # Allow audio callback function to be called again
        SDL_UnlockAudioDevice(self.audio_callback_data.device_id)

        self.log.debug("The '%s' live loop track has successfully been created.", name)

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
        return SoundMemoryFile(file_name,
                               self.audio_callback_data.sample_rate,
                               self.audio_callback_data.format,
                               self.audio_callback_data.channels,
                               self.audio_callback_data.buffer_size)

    def unload_sound_file_from_memory(self, container not None):
        """
        Unloads the source sample from the supplied container (used in Sound
        asset unloading).  The sound will no longer be in memory.
        Args:
            container: A SoundMemoryFile object
        """
        if not isinstance(container, SoundMemoryFile):
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


        # Process any internal sound messages that may affect sound playback (play and stop messages)
        process_request_messages(callback_data)

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

                # Apply ducking to track audio buffer (when applicable)
                apply_track_ducking(callback_data.tracks[track_num], buffer_length, callback_data)

                # Apply track volume and mix to output buffer
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

cdef void process_request_messages(AudioCallbackData *callback_data) nogil:
    """
    Processes any new request messages that should be processed prior to the main
    audio callback processing (such as sound play and sound stop messages).
    Args:
        callback_data: The audio callback data structure
    """
    cdef int track_num
    cdef TrackState *track

    # Loop over all the tracks
    for track_num in range(callback_data.track_count):
        track = callback_data.tracks[track_num]

        # Reverse the list since the messages were added in reverse order for efficiency
        track.request_messages = g_slist_reverse(track.request_messages)

        # Process the request message list based on the track type
        if track.type == track_type_standard:
            g_slist_foreach(track.request_messages, <GFunc>process_standard_track_request_message, track)
        elif track.type == track_type_playlist:
            # TODO: Implement track request message function call
            #g_slist_foreach(track.request_messages, <GFunc>process_playlist_request_message, track)
            pass
        elif track.type == track_type_live_loop:
            # TODO: Implement track request message function call
            #g_slist_foreach(track.request_messages, <GFunc>process_live_loop_request_message, track)
            pass

        # Free the linked list.
        # IMPORTANT: the list item processing functions must free the request message memory of there
        # will be a big memory leak here!
        g_slist_free(track.request_messages)
        track.request_messages = NULL

cdef void process_standard_track_request_message(RequestMessageContainer *request_message,
                                                 TrackState *track) nogil:
    """
    Processes any new standard track request messages that should be processed prior to the
    main audio callback processing (such as sound play and sound stop messages).  This function
    is called in the SDL callback thread.
    Args:
        request_message: The request message to process
        track: The TrackState struct for this track
    """
    cdef SoundPlayer *player
    cdef TrackStandardState *standard_track

    if track.type != track_type_standard or track.type_state == NULL:
        return

    standard_track = <TrackStandardState*>track.type_state
    player = cython.address(standard_track.sound_players[request_message.player])

    if request_message.message == request_sound_play:
        # Update player to start playing new sound
        player.status = player_playing
        player.current.sample_pos = request_message.data.play.start_at_position
        player.current.current_loop = 0
        player.current.sound_id = request_message.sound_id
        player.current.sound_instance_id = request_message.sound_instance_id
        player.current.sample = request_message.data.play.sample
        player.current.volume = request_message.data.play.volume
        player.current.loops_remaining = request_message.data.play.loops
        player.current.sound_priority = request_message.data.play.priority

        # Fading (done at control rate; need to calculate the number of steps over which to fade in/out)
        player.current.fade_in_steps = request_message.data.play.fade_in_duration // track.callback_data.bytes_per_control_point
        player.current.fade_out_steps = request_message.data.play.fade_out_duration // track.callback_data.bytes_per_control_point
        player.current.fade_steps_remaining = player.current.fade_in_steps
        if player.current.fade_steps_remaining > 0:
            player.current.fading_status = fading_status_fading_in
        else:
            player.current.fading_status = fading_status_not_fading

        # Markers
        player.current.marker_count = request_message.data.play.marker_count

        for index in range(request_message.data.play.marker_count):
            player.current.markers[index] = request_message.data.play.markers[index]

        if request_message.data.play.sound_has_ducking:
            player.current.sound_has_ducking = True
            player.current.ducking_settings.track_bit_mask = request_message.data.play.ducking_settings.track_bit_mask
            player.current.ducking_settings.attack_start_pos = request_message.data.play.ducking_settings.attack_start_pos
            player.current.ducking_settings.attack_duration = request_message.data.play.ducking_settings.attack_duration
            player.current.ducking_settings.attenuation_volume = request_message.data.play.ducking_settings.attenuation_volume
            player.current.ducking_settings.release_start_pos = request_message.data.play.ducking_settings.release_start_pos
            player.current.ducking_settings.release_duration = request_message.data.play.ducking_settings.release_duration
            player.current.ducking_stage = ducking_stage_delay

        else:
            player.current.sound_has_ducking = False

        # Send sound started notification
        send_sound_started_notification(request_message.player, player.current.sound_id, player.current.sound_instance_id, track)

    elif request_message.message == request_sound_stop:
        # Update player to stop playing sound

        # Calculate fade out (if necessary)
        player.current.fade_steps_remaining = request_message.data.stop.fade_out_duration // track.callback_data.bytes_per_control_point
        if player.current.fade_steps_remaining > 0:
            player.current.fade_out_steps = player.current.fade_steps_remaining
            player.current.fading_status = fading_status_fading_out
            player.status = player_stopping
        else:
            # Sound will stop immediately - send sound stopped notification
            send_sound_stopped_notification(request_message.player, player.current.sound_id, player.current.sound_instance_id, track)
            player.status = player_idle

        # Adjust ducking release (if necessary)
        if player.current.sound_has_ducking:
            # player.current.ducking_settings.release_duration = request_message.data.stop.ducking_release_duration
            # player.current.ducking_settings.release_start_pos = player.current.sample_pos
            # TODO: Add more intelligent ducking release point calculation here:
            #       Take into consideration whether ducking is already in progress and when it was
            #       originally scheduled to finish.
            pass

    elif request_message.message == request_sound_replace:
        # Update player to stop playing current sound and start playing new sound
        player.status = player_replacing

        # Set current sound to fade out quickly
        player.current.fade_out_steps = track.callback_data.quick_fade_steps
        player.current.fade_steps_remaining = track.callback_data.quick_fade_steps
        player.current.fading_status = fading_status_fading_out

        # Setup next sound
        player.next.sample_pos = request_message.data.play.start_at_position
        player.next.current_loop = 0
        player.next.sound_id = request_message.sound_id
        player.next.sound_instance_id = request_message.sound_instance_id
        player.next.sample = request_message.data.play.sample
        player.next.volume = request_message.data.play.volume
        player.next.loops_remaining = request_message.data.play.loops
        player.next.sound_priority = request_message.data.play.priority

        # Fading (done at control rate; need to calculate the number of steps over which to fade in/out)
        player.next.fade_in_steps = request_message.data.play.fade_in_duration // track.callback_data.bytes_per_control_point
        player.next.fade_out_steps = request_message.data.play.fade_out_duration // track.callback_data.bytes_per_control_point
        player.next.fade_steps_remaining = player.next.fade_in_steps
        if player.next.fade_steps_remaining > 0:
            player.next.fading_status = fading_status_fading_in
        else:
            player.next.fading_status = fading_status_not_fading

        # Markers
        player.next.marker_count = request_message.data.play.marker_count

        for index in range(request_message.data.play.marker_count):
            player.next.markers[index] = request_message.data.play.markers[index]

        if request_message.data.play.sound_has_ducking:
            player.next.sound_has_ducking = True
            player.next.ducking_settings.track_bit_mask = request_message.data.play.ducking_settings.track_bit_mask
            player.next.ducking_settings.attack_start_pos = request_message.data.play.ducking_settings.attack_start_pos
            player.next.ducking_settings.attack_duration = request_message.data.play.ducking_settings.attack_duration
            player.next.ducking_settings.attenuation_volume = request_message.data.play.ducking_settings.attenuation_volume
            player.next.ducking_settings.release_start_pos = request_message.data.play.ducking_settings.release_start_pos
            player.next.ducking_settings.release_duration = request_message.data.play.ducking_settings.release_duration
            player.next.ducking_stage = ducking_stage_delay

        else:
            player.next.sound_has_ducking = False

        # TODO: Figure out how to handle ducking when replacing an existing sound

        # Free request message memory since it has been processed
        g_slice_free1(sizeof(RequestMessageContainer), request_message)

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

    Args:
        sound:
        length:
        output_buffer:
        volume:
        track:
        player_num

    Returns:
        True if sound is finished, False otherwise
    """
    if sound == NULL or output_buffer == NULL:
        return True

    cdef Uint32 buffer_pos = 0
    cdef Uint8 *sound_buffer = <Uint8*>sound.sample.data.memory.data
    if sound_buffer == NULL:
        return True

    while buffer_pos < length:
        # Mix the sound sample to the output buffer
        SDL_MixAudioFormat(output_buffer + buffer_pos, sound_buffer + sound.sample_pos,
                           track.callback_data.format, track.callback_data.bytes_per_sample, volume)

        # Advance to next sample
        buffer_pos += track.callback_data.bytes_per_sample
        sound.sample_pos += track.callback_data.bytes_per_sample

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

    Args:
        sound:
        length:
        output_buffer:
        volume:
        track:
        player_num

    Returns:
        True if sound is finished, False otherwise
    """
    if sound == NULL or output_buffer == NULL or sound.sample.data.stream.pipeline == NULL:
        return True

    cdef Uint32 samples_remaining_to_output = length
    cdef Uint32 samples_remaining_in_map
    cdef Uint32 buffer_pos = 0
    cdef gboolean is_eos

    while samples_remaining_to_output > 0:

        # Copy any samples remaining in the buffer from the last call
        if sound.sample.data.stream.map_contains_valid_sample_data:
            samples_remaining_in_map = sound.sample.data.stream.map_info.size - sound.sample.data.stream.map_buffer_pos
            # Determine if we are consuming the entire buffer of leftover samples
            if samples_remaining_to_output < samples_remaining_in_map:
                # We are not consuming the entire buffer of leftover samples.  There will still be some for the next call.
                SDL_MixAudioFormat(output_buffer + buffer_pos, sound.sample.data.stream.map_info.data + sound.sample.data.stream.map_buffer_pos, track.callback_data.format, samples_remaining_to_output, volume)
                sound.sample.data.stream.map_buffer_pos += samples_remaining_to_output
                sound.sample_pos += samples_remaining_to_output
                return False
            else:
                # Entire buffer of leftover samples consumed.  Free the buffer resources to prepare for next call
                SDL_MixAudioFormat(output_buffer + buffer_pos, sound.sample.data.stream.map_info.data + sound.sample.data.stream.map_buffer_pos, track.callback_data.format, samples_remaining_in_map, volume)
                samples_remaining_to_output -= samples_remaining_in_map
                sound.sample_pos += samples_remaining_in_map

                gst_buffer_unmap(sound.sample.data.stream.buffer, &sound.sample.data.stream.map_info)
                gst_sample_unref(sound.sample.data.stream.sample)
                gst_buffer_unref(sound.sample.data.stream.buffer)
                sound.sample.data.stream.buffer = NULL
                sound.sample.data.stream.sample = NULL
                sound.sample.data.stream.map_buffer_pos = 0
                sound.sample.data.stream.map_contains_valid_sample_data = 0

        # Check for EOS (end of stream)
        is_eos = g_object_get_bool(sound.sample.data.stream.sink, "eos")
        if is_eos:
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

            gst_element_seek_simple(sound.sample.data.stream.pipeline, GST_FORMAT_TIME, <GstSeekFlags>(GST_SEEK_FLAG_FLUSH | GST_SEEK_FLAG_KEY_UNIT), 0)
            return False

        # Retrieve the next buffer from the pipeline
        sound.sample.data.stream.sample = c_appsink_pull_sample(sound.sample.data.stream.sink)
        if sound.sample.data.stream.sample == NULL:
            sound.sample.data.stream.null_buffer_count += 1

            # If we've received too many consecutive null buffers, end the sound
            if sound.sample.data.stream.null_buffer_count > CONSECUTIVE_NULL_STREAMING_BUFFER_LIMIT:
                return True
        else:
            sound.sample.data.stream.null_buffer_count = 0
            sound.sample.data.stream.buffer = gst_sample_get_buffer(sound.sample.data.stream.sample)

            if not gst_buffer_map(sound.sample.data.stream.buffer, &sound.sample.data.stream.map_info, GST_MAP_READ):
                gst_sample_unref(sound.sample.data.stream.sample)
                sound.sample.data.stream.sample = NULL


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
        send_sound_looping_notification(player.player,
                                 player.current.sound_id, player.current.sound_instance_id,
                                 track)

    elif player.current.loops_remaining == 0:
        # At the end and not looping, the sample has finished playing
        player.status = player_finished

    else:
        # Looping infinitely, loop back to the beginning
        player.current.sample_pos = 0
        player.current.current_loop += 1
        send_sound_looping_notification(player.player,
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

cdef void apply_track_ducking(TrackState* track, Uint32 buffer_size, AudioCallbackData* callback_data) nogil:
    """
    Applies ducking to the specified track (if applicable).
    Args:
        track: A pointer to the TrackState struct for the track
        buffer_size: The size of the current output audio buffer (in bytes)
        callback_data: The AudioCallbackData struct
    """
    cdef Uint32 buffer_pos = 0
    cdef Uint8 ducking_volume
    cdef int control_point = 0

    if track == NULL:
        return

    # Only need to process when ducking is active
    if track.ducking_is_active:
        # Loop over track buffer
        while buffer_pos < buffer_size and control_point < CONTROL_POINTS_PER_BUFFER:
            ducking_volume = track.ducking_control_points[control_point]
            if ducking_volume < SDL_MIX_MAXVOLUME:
                apply_volume_to_buffer_range(<Uint8*> track.buffer, buffer_pos, ducking_volume, callback_data.bytes_per_control_point)

            buffer_pos += callback_data.bytes_per_control_point
            control_point += 1

cdef inline void apply_volume_to_buffer_range(Uint8 *buffer, Uint32 start_pos, Uint8 volume, Uint32 length=2) nogil:
    """
    Applies the specified volume to a range of samples in an audio buffer at the specified
    buffer position.
    Args:
        buffer: The audio buffer
        start_pos: The starting audio buffer position at which to apply the volume level
        volume: The volume level to apply (8-bit unsigned value 0 to SDL_MIX_MAXVOLUME)
        length: The number of bytes to apply the volume to
    """
    cdef Sample16Bit buffer_sample
    cdef Uint32 buffer_pos = start_pos

    while buffer_pos < start_pos + length:
        buffer_sample.bytes.byte0 = buffer[buffer_pos]
        buffer_sample.bytes.byte1 = buffer[buffer_pos + 1]
        buffer_sample.value = (buffer_sample.value * volume) // SDL_MIX_MAXVOLUME
        buffer[buffer_pos] = buffer_sample.bytes.byte0
        buffer[buffer_pos + 1] = buffer_sample.bytes.byte1
        buffer_pos += BYTES_PER_SAMPLE

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
                              Uint8 *output_buffer, Uint32 buffer_size) nogil:
    """
    Mixes a track buffer into the master audio output buffer.
    Args:
        track: The track's state structure
        callback_data: The audio callback data structure
        output_buffer: The master audio output buffer.
        buffer_size: The audio buffer size to process.

    """

    cdef Sample16Bit track_sample
    cdef Sample16Bit output_sample
    cdef int temp_sample
    cdef Uint32 index
    cdef Uint8 *track_buffer
    cdef Uint32 samples_per_control_point

    index = 0

    if track == NULL or track.status == track_status_stopped or track.status == track_status_paused:
        return

    track_buffer = <Uint8*>track.buffer

    # Determine if track is currently fading
    if track.fade_steps_remaining > 0:
        # A fade is in progress, apply fade to track buffer when mixing to output
        samples_per_control_point = track.buffer_size // CONTROL_POINTS_PER_BUFFER
        while index < buffer_size:

            # Calculate volume at the control rate (handle fading)
            if (index % samples_per_control_point) == 0:
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

            # Get sound sample (2 bytes), combine into a 16-bit value and apply sound volume
            track_sample.bytes.byte0 = track_buffer[index]
            track_sample.bytes.byte1 = track_buffer[index + 1]
            track_sample.value = track_sample.value * track.fade_volume_current // SDL_MIX_MAXVOLUME

            # Get sample (2 bytes) already in the output buffer and combine into 16-bit value
            output_sample.bytes.byte0 = output_buffer[index]
            output_sample.bytes.byte1 = output_buffer[index + 1]

            # Calculate the new output sample (mix the existing output sample with
            # the track sample).  The temp sample is a 32-bit value to avoid overflow.
            temp_sample = output_sample.value + track_sample.value

            # Clip the temp sample back to a 16-bit value (will cause distortion if samples
            # on channel are too loud)
            if temp_sample > MAX_AUDIO_VALUE_S16:
                temp_sample = MAX_AUDIO_VALUE_S16
            elif temp_sample < MIN_AUDIO_VALUE_S16:
                temp_sample = MIN_AUDIO_VALUE_S16

            # Write the new output sample back to the output buffer (from
            # a 32-bit value back to a 16-bit value that we know is in 16-bit value range)
            output_sample.value = temp_sample
            output_buffer[index] = output_sample.bytes.byte0
            output_buffer[index + 1] = output_sample.bytes.byte1

            index += callback_data.bytes_per_sample

    else:
        # No fade in progress: volume is constant over entire output buffer
        SDL_MixAudioFormat(output_buffer, track_buffer, callback_data.format, buffer_size, track.volume)

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
    cdef list _events_when_resumed
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
        self._events_when_resumed = None

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

        self.state.request_messages = NULL
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
    def events_when_resumed(self):
        """Return the list of events that are posted when the track is resumed"""
        return self._events_when_resumed

    @events_when_resumed.setter
    def events_when_resumed(self, events):
        """Sets the list of events that are posted when the track is resumed"""
        self._events_when_resumed = events

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

        # Play is only supported when a track is stopped or is in the process of stopping
        if self.state.status == track_status_stopped or self.state.status == track_status_stopping:
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

    def resume(self, float fade_in_seconds = 0.0):
        """
        Resumes playing a paused track so it can continue processing sounds. Function has no effect
        unless the track is paused.
        Args:
            fade_in_seconds: The number of seconds to fade in the track
        """
        self.log.debug("resume - Resume sound processing on track")

        SDL_LockAudioDevice(self.device_id)

        # Play is only supported when a track is paused or is in the process of pausing
        if self.state.status == track_status_paused or self.state.status == track_status_pausing:
            if fade_in_seconds > 0:
                # Calculate fade data (steps and volume)
                self.log.debug("resume - Applying %s second fade in", str(fade_in_seconds))
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
            if self.events_when_resumed is not None:
                for event in self.events_when_resumed:
                    self.mc.post_mc_native_event(event)
        else:
            self.log.warning("resume - Action may only be used when a track is paused or is in the process "
                             "of pausing; action will be ignored.")

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

    def play_sound(self, sound_instance not None):
        """
        Plays a sound on the current track.
        Args:
            sound_instance: The SoundInstance object to play
        """
        raise NotImplementedError('Must be overridden in derived class')

    def stop_sound(self, sound_instance not None):
        """
        Stops all instances of the specified sound immediately on the track.
        Args:
            sound_instance: The SoundInstance to stop
        """
        raise NotImplementedError('Must be overridden in derived class')

    def stop_sound_looping(self, sound_instance not None):
        """
        Stops all instances of the specified sound on the track after they finish the current loop.
        Any queued instances of the sound will be removed.
        Args:
            sound_instance: The Sound to stop
        """
        raise NotImplementedError('Must be overridden in derived class')

    def stop_all_sounds(self, float fade_out_seconds = 0.0):
        """
        Stops all playing sounds immediately on the track.
        Args:
            fade_out_seconds: The number of seconds to fade out the sounds before stopping
        """
        raise NotImplementedError('Must be overridden in derived class')

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
            self.type_state.sound_players[i].player = i
            self.type_state.sound_players[i].current.sample = NULL
            self.type_state.sound_players[i].current.loops_remaining = 0
            self.type_state.sound_players[i].current.current_loop = 0
            self.type_state.sound_players[i].current.volume = 0
            self.type_state.sound_players[i].current.sample_pos = 0
            self.type_state.sound_players[i].current.sound_id = 0
            self.type_state.sound_players[i].current.sound_instance_id = 0
            self.type_state.sound_players[i].current.sound_priority = 0
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
            self.type_state.sound_players[i].next.sound_has_ducking = False
            self.type_state.sound_players[i].next.ducking_stage = ducking_stage_idle

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
        return False

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

    cdef inline RequestMessageContainer* _create_request_message(self):
        """
        Returns a pointer to a new request message container
        """
        return <RequestMessageContainer*>g_slice_alloc0(sizeof(RequestMessageContainer))

    cdef inline void _add_request_message(self, RequestMessageContainer* request_message):
        """
        Adds the request message to the queue of request messages
        """
        # Note: we are prepending the item to the list (more efficient), however this means the
        # list is in the reverse order and should be reversed before processing.
        self.state.request_messages = g_slist_prepend(self.state.request_messages, request_message)

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

        return None

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

        SDL_LockAudioDevice(self.device_id)

        self.log.debug("Stopping sound %s and removing any pending instances from queue", sound_instance.name)

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and self.type_state.sound_players[
                i].current.sound_instance_id == sound_instance.id:
                # Set stop sound event
                request_message = self._create_request_message()
                if request_message != NULL:
                    request_message.message = request_sound_stop
                    request_message.sound_id = self.type_state.sound_players[i].current.sound_id
                    request_message.sound_instance_id = self.type_state.sound_players[i].current.sound_instance_id
                    request_message.player = i

                    # Fade out
                    request_message.data.stop.fade_out_duration = sound_instance.fade_out * self.state.callback_data.seconds_to_bytes_factor

                    # Adjust ducking (if necessary)
                    if sound_instance.ducking is not None:
                        request_message.data.stop.ducking_release_duration = min(
                            sound_instance.ducking.release * self.state.callback_data.seconds_to_bytes_factor,
                            request_message.data.stop.fade_out_duration)

                    self._add_request_message(request_message)
                else:
                    self.log.error(
                        "All internal audio messages are currently "
                        "in use, could not stop sound %s", sound_instance.name)

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
                # Set stop sound event
                request_message = self._create_request_message()
                if request_message != NULL:
                    request_message.message = request_sound_stop
                    request_message.sound_id = self.type_state.sound_players[i].current.sound_id
                    request_message.sound_instance_id = self.type_state.sound_players[i].current.sound_instance_id
                    request_message.player = i

                    # Fade out
                    request_message.data.stop.fade_out_duration = <Uint32>(fade_out_seconds * self.state.callback_data.seconds_to_bytes_factor)

                    # Adjust ducking (if necessary)
                    # TODO: trigger ducking here

                    self._add_request_message(request_message)
                else:
                    self.log.error("All internal audio messages are currently in use, could not stop all sounds")

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

        # Get the sound sample buffer container
        cdef SoundFile sound_container = sound_instance.container
        cdef RequestMessageContainer *request_message

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

            # Set play sound event
            request_message = self._create_request_message()
            if request_message != NULL:

                # Add sound to the dictionary of active sound instances
                self.log.debug("Adding sound instance %s to active sound dictionary", str(sound_instance))
                self._sound_instances_by_id[sound_instance.id] = sound_instance

                if self.type_state.sound_players[player].status != player_idle:
                    request_message.message = request_sound_replace
                else:
                    # Reserve the sound player for this sound (it is no longer idle)
                    self.type_state.sound_players[player].status = player_pending
                    request_message.message = request_sound_play

                request_message.sound_id = sound_instance.sound.id
                request_message.sound_instance_id = sound_instance.id
                request_message.player = player
                request_message.data.play.loops = sound_instance.loops
                request_message.data.play.priority = sound_instance.priority
                request_message.data.play.sample = cython.address(sound_container.sample)

                # Conversion factor (seconds to bytes/buffer position)
                request_message.data.play.start_at_position = <Uint32>(sound_instance.start_at * self.state.callback_data.seconds_to_bytes_factor)
                request_message.data.play.fade_in_duration = <Uint32>(sound_instance.fade_in * self.state.callback_data.seconds_to_bytes_factor)
                request_message.data.play.fade_out_duration = <Uint32>(sound_instance.fade_out * self.state.callback_data.seconds_to_bytes_factor)

                # Volume must be converted from a float (0.0 to 1.0) to an 8-bit integer (0..SDL_MIX_MAXVOLUME)
                request_message.data.play.volume = <Uint8>(sound_instance.volume * SDL_MIX_MAXVOLUME)

                # If the sound has any markers, set them
                request_message.data.play.marker_count = sound_instance.marker_count
                if sound_instance.marker_count > 0:
                    for index in range(sound_instance.marker_count):
                        request_message.data.play.markers[index] = <long>(sound_instance.markers[index]['time'] * self.state.callback_data.seconds_to_bytes_factor)

                # If the sound has ducking settings, apply them
                if sound_instance.ducking is not None and sound_instance.ducking.track_bit_mask != 0:
                    # To convert between the number of seconds and a buffer position (bytes), we need to
                    # account for the sample rate (sampes per second), the number of audio channels, and the
                    # number of bytes per sample (all samples are 16 bits)
                    request_message.data.play.sound_has_ducking = True
                    request_message.data.play.ducking_settings.track_bit_mask = sound_instance.ducking.track_bit_mask
                    request_message.data.play.ducking_settings.attack_start_pos = sound_instance.ducking.delay * self.state.callback_data.seconds_to_bytes_factor
                    request_message.data.play.ducking_settings.attack_duration = sound_instance.ducking.attack * self.state.callback_data.seconds_to_bytes_factor
                    request_message.data.play.ducking_settings.attenuation_volume = <Uint8>(sound_instance.ducking.attenuation * SDL_MIX_MAXVOLUME)
                    request_message.data.play.ducking_settings.release_start_pos = sound_instance.ducking.release_point * self.state.callback_data.seconds_to_bytes_factor
                    request_message.data.play.ducking_settings.release_duration = sound_instance.ducking.release * self.state.callback_data.seconds_to_bytes_factor
                else:
                    request_message.data.play.sound_has_ducking = False
    
                self._add_request_message(request_message)

                # Special handling is needed to start streaming for the specified sound
                if sound_instance.container.sample.type == sound_type_streaming:
                    # Seek to the specified start position
                    gst_element_seek_simple(sound_instance.container.sample.data.stream.pipeline,
                                            GST_FORMAT_TIME,
                                            <GstSeekFlags>(GST_SEEK_FLAG_FLUSH | GST_SEEK_FLAG_KEY_UNIT),
                                            sound_instance.start_at * GST_SECOND)
                    with nogil:
                        ret = gst_element_set_state(sound_instance.container.sample.data.stream.pipeline, GST_STATE_PLAYING)

            else:
                self.log.warning("All internal audio messages are "
                               "currently in use, could not play sound %s"
                               , sound_instance.name)
                SDL_UnlockAudioDevice(self.device_id)
                return False

            self.log.debug("Sound %s is set to begin playback on player %d (loops=%d)",
                           sound_instance.name, player, sound_instance.loops)

            SDL_UnlockAudioDevice(self.device_id)
            return True

        SDL_UnlockAudioDevice(self.device_id)
        return False

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
#    TrackLiveLoop class
# ---------------------------------------------------------------------------
cdef class TrackLiveLoop(Track):
    """
    TrackLiveLoop class
    """

    # Track state needs to be stored in a C struct in order for them to be accessible in
    # the SDL callback functions without the GIL (for performance reasons).
    # The TrackLiveLoopState struct is allocated during construction and freed during
    # destruction.
    cdef TrackLiveLoopState *type_state

    def __cinit__(self, *args, **kw):
        """C Constructor"""
        self.type_state = NULL

    def __init__(self, object mc, object audio_callback_data, str name, int track_num, int buffer_size,
                 float volume=1.0):
        """
        Constructor
        Args:
            mc: The media controller object
            audio_callback_data: The AudioCallbackData struct wrapped in a PyCapsule
            name: The track name
            track_num: The track number
            buffer_size: The length of the track audio buffer in bytes
            volume: The track volume (0.0 to 1.0)
        """
        # IMPORTANT: Call super class init function to allocate track state memory!
        super().__init__(mc, audio_callback_data, name, track_num, buffer_size, volume)

        self.log = logging.getLogger("Track." + str(track_num) + ".TrackLiveLoop")

        SDL_LockAudioDevice(self.device_id)

        # Set track type specific settings
        self.state.type = track_type_live_loop

        # Allocate memory for the specific track type state struct (TrackLiveLoopState)
        self.type_state = <TrackLiveLoopState*> PyMem_Malloc(sizeof(TrackLiveLoopState))
        self.state.type_state = <void*>self.type_state

        self.type_state.master_sound_player = <SoundPlayer*> PyMem_Malloc(sizeof(SoundPlayer))
        self.type_state.slave_sound_player_count = 0
        self.type_state.slave_sound_players = NULL

        # TODO: Allocate slave sound players

        SDL_UnlockAudioDevice(self.device_id)

    def __dealloc__(self):
        """Destructor"""

        SDL_LockAudioDevice(self.device_id)

        # Free the specific track type state and other allocated memory
        if self.type_state != NULL:
            if self.type_state.master_sound_player != NULL:
                PyMem_Free(self.type_state.master_sound_player)

            # TODO: Clean-up slave sound players
            #for player in range(self.type_state.slave_sound_player_count):
            #    PyMem_Free(self.type_state.slave_sound_players[player])

            PyMem_Free(self.type_state)
            self.type_state = NULL
            self.state.type_state = NULL

        SDL_UnlockAudioDevice(self.device_id)

    def __repr__(self):
        return '<Track.{}.LiveLoop.{}>'.format(self.number, self.name)

    @property
    def supports_in_memory_sounds(self):
        """Return whether or not track supports in-memory sounds"""
        return True

    @property
    def supports_streaming_sounds(self):
        """Return whether or not track supports streaming sounds"""
        return False

    def play_sound(self, sound_instance not None):
        """
        Plays a sound on the current track.
        Args:
            sound_instance: The SoundInstance object to play
        """
        self.log.debug("play_sound - Processing sound '%s' for playback (%s).", sound_instance.name)

        # Make sure the sound is loaded and therefore ready to play immediately.

        SDL_LockAudioDevice(self.device_id)

        # TODO: play the sound instance

        SDL_UnlockAudioDevice(self.device_id)

    def stop_sound(self, sound_instance not None):
        """
        Stops all instances of the specified sound immediately on the track. Any queued instances
        will be removed from the queue.
        Args:
            sound_instance: The SoundInstance to stop
        """

        SDL_LockAudioDevice(self.device_id)

        # TODO: stop the sound instance

        SDL_UnlockAudioDevice(self.device_id)

    def stop_sound_looping(self, sound_instance not None):
        """
        Stops all instances of the specified sound on the track after they finish the current loop.
        Any queued instances of the sound will be removed.
        Args:
            sound_instance: The Sound to stop
        """

        SDL_LockAudioDevice(self.device_id)

        # TODO: stop looping the sound instance

        SDL_UnlockAudioDevice(self.device_id)

    def stop_all_sounds(self, float fade_out_seconds = 0.0):
        """
        Stops all playing sounds immediately on the track.
        """
        SDL_LockAudioDevice(self.device_id)

        # TODO: stop looping the sound instance

        SDL_UnlockAudioDevice(self.device_id)

    def process(self):
        """Processes the track queue each tick."""
        pass


# ---------------------------------------------------------------------------
#    SoundFile class
# ---------------------------------------------------------------------------
cdef class SoundFile:
    """SoundMemoryFile is the base class for wrapper classes used to manage sound sample data."""
    cdef str file_name
    cdef int sample_rate
    cdef SDL_AudioFormat format
    cdef Uint8 channels
    cdef buffer_size
    cdef SoundSample sample

    def __init__(self, str file_name, int sample_rate, SDL_AudioFormat format, int channels, int buffer_size):
        self.file_name = file_name
        self.sample_rate = sample_rate
        self.format = format
        self.channels = <Uint8>channels
        self.buffer_size = buffer_size

    def __repr__(self):
        return '<SoundFile>'

    def load(self):
        """Load the sound file"""
        raise NotImplementedError("Must be implemented in derived class")

    def unload(self):
        """Unload the sound file"""
        raise NotImplementedError("Must be implemented in derived class")


# ---------------------------------------------------------------------------
#    SoundMemoryFile class
# ---------------------------------------------------------------------------
cdef class SoundMemoryFile(SoundFile):
    """SoundMemoryFile is a wrapper class to manage sound sample data stored
    in memory."""
    cdef bint _loaded_using_sdl

    def __init__(self, str file_name, int sample_rate, SDL_AudioFormat format, int channels, int buffer_size):
        # IMPORTANT: Call super class init function
        super().__init__(file_name, sample_rate, format, channels, buffer_size)
        self.sample.type = sound_type_memory
        self.sample.data.memory = <SampleMemory*>PyMem_Malloc(sizeof(SampleMemory))
        self.sample.data.memory.data = NULL
        self.sample.data.memory.size = 0
        self._loaded_using_sdl = False

        self.load()

    def __dealloc__(self):
        self.unload()
        if self.sample.data.memory != NULL:
            PyMem_Free(self.sample.data.memory)

    def __repr__(self):
        if self.sample.data.memory.data == NULL:
            return '<SoundMemoryFile(Loaded=False)>'
        return '<SoundMemoryFile(Loaded=True, {} bytes)>'.format(self.sample.data.memory.size)

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

    def load(self):
        """Loads the sound into memory using the most appropriate library for the format."""

        if self.loaded:
            return

        if not os.path.isfile(self.file_name):
            raise AudioException('Could not locate file ' + self.file_name)

        #return self._load_using_gstreamer()

        # Determine which loader to use based on the file extension
        if os.path.splitext(self.file_name)[1].lower() == ".wav":
            # Wave files are loaded using SDL2 (very fast)
            self._load_using_sdl()
        else:
            # All other formats are loaded using GStreamer
            self._load_using_gstreamer()

    def _load_using_sdl(self):
        """Loads the sound into memory using SDL2 (much faster than GStreamer, but only
        supports WAV files."""
        cdef SDL_AudioSpec wave_spec
        cdef SDL_AudioSpec desired_spec
        cdef SDL_AudioSpec *loaded
        cdef SDL_AudioCVT wavecvt
        cdef Uint8 *temp_sample_data = NULL
        cdef Uint32 temp_sample_size = 0
        cdef Uint8* converted_sample_data = NULL
        cdef Uint32 converted_sample_size = 0

        self._loaded_using_sdl = True
        print("Loading sound asset using SDL", self.file_name)

        # Load the WAV file into memory (memory is allocated during the load)
        loaded = SDL_LoadWAV(self.file_name.encode('utf-8'), &wave_spec, &temp_sample_data, &temp_sample_size)
        if loaded == NULL:
            msg = "Could not load sound file {} due to an error: {}".format(self.file_name, SDL_GetError())
            print(msg)
            raise AudioException(msg)

        desired_spec.freq = self.sample_rate
        desired_spec.format = self.format
        desired_spec.channels = self.channels

        print("Sound file loaded spec", wave_spec.freq, wave_spec.format, wave_spec.channels, temp_sample_size)

        if wave_spec.freq != self.sample_rate or wave_spec.format != self.format or wave_spec.channels != self.channels:
            print("Conversion needed")

            # Now we need to check if the audio format must be converted to match the audio interface output format
            if convert_audio_to_desired_format(wave_spec, desired_spec, temp_sample_data, temp_sample_size, &converted_sample_data, &converted_sample_size) < 0:
                SDL_FreeWAV(temp_sample_data)
                msg = "Could not convert sound file {} to required format".format(self.file_name)
                print(msg)
                raise AudioException(msg)

            else:
                # Reallocate sample buffer as it is very possible it shrank during the conversion process
                self.sample.data.memory.size = <gsize>converted_sample_size
                self.sample.data.memory.data = <gpointer>converted_sample_data
                SDL_FreeWAV(temp_sample_data)

        else:
            self.sample.data.memory.size = <gsize>temp_sample_size
            self.sample.data.memory.data = <gpointer>temp_sample_data

    def _load_using_gstreamer(self):
        """Loads the sound into memory using GStreamer"""
        cdef str pipeline_string
        cdef str file_path
        cdef GstElement *pipeline
        cdef GstElement *sink
        cdef GError *error
        cdef GstStateChangeReturn ret
        cdef GstState state
        cdef GstSample *sample
        cdef GstBuffer *buffer
        cdef GstMapInfo map_info
        cdef gboolean is_eos

        self._loaded_using_sdl = False
        self._gst_init()

        # Pipeline structure: uridecodebin --> audioconvert --> audioresample --> appsink

        # Create GStreamer pipeline with the specified caps (from a string)
        file_path = 'file:///' + self.file_name.replace('\\', '/')
        if SDL_AUDIO_ISLITTLEENDIAN(self.format):
            audio_format = "S16LE"
        else:
            audio_format = "S16BE"
        pipeline_string = 'uridecodebin uri="{}" ! audioconvert ! audioresample ! appsink name=sink caps="audio/x-raw,rate={},channels={},format={},layout=interleaved" sync=false blocksize=44100'.format(
            file_path, str(self.sample_rate), str(self.channels), audio_format)

        print(pipeline_string)

        error = NULL
        pipeline = gst_parse_launch(pipeline_string.encode('utf-8'), &error)

        if error != NULL:
            msg = 'Unable to create a GStreamer pipeline: code={} message={}'.format(error.code, <bytes>error.message)
            raise AudioException(msg)

        # Get sink
        sink = gst_bin_get_by_name(<GstBin*>pipeline, "sink")

        # Set to PAUSED to make the first frame arrive in the sink
        #ret = gst_element_set_state(pipeline, GST_STATE_PAUSED)

        # get ready!
        with nogil:
            ret = gst_element_set_state(pipeline, GST_STATE_PLAYING)

        while True:
            sample = c_appsink_pull_sample(sink)
            if sample == NULL:
                break

            is_eos = g_object_get_bool(sink, "eos")
            if is_eos:
                break

            buffer = gst_sample_get_buffer(sample)

            if not gst_buffer_map(buffer, &map_info, GST_MAP_READ):
                gst_sample_unref(sample)
                if self.sample.data.memory.data != NULL:
                    g_free(self.sample.data.memory.data)
                    self.sample.data.memory.data = NULL
                    self.sample.data.memory.size = 0
                raise AudioException("Unable to map GStreamer buffer")

            if self.sample.data.memory.data == NULL:
                self.sample.data.memory.data = PyMem_Malloc(map_info.size)
                self.sample.data.memory.size = map_info.size
                memcpy(self.sample.data.memory.data, map_info.data, map_info.size)
            else:
                self.sample.data.memory.data = PyMem_Realloc(self.sample.data.memory.data, self.sample.data.memory.size + map_info.size)
                memcpy(self.sample.data.memory.data + self.sample.data.memory.size, map_info.data, map_info.size)
                self.sample.data.memory.size += map_info.size

            gst_buffer_unmap(buffer, &map_info)
            gst_sample_unref(sample)

        # Copy the sound data to it's permanent home
        print("Final sample data length: ", self.sample.data.memory.size)

        # Cleanup the loader pipeline
        gst_element_set_state(pipeline, GST_STATE_NULL)
        gst_object_unref (pipeline)

    def unload(self):
        """Unloads the sample data from memory"""
        if self.sample.data.memory.data != NULL:
            if self._loaded_using_sdl:
                SDL_FreeWAV(<Uint8*>self.sample.data.memory.data)
            else:
                PyMem_Free(self.sample.data.memory.data)

            self.sample.data.memory.data = NULL
            self.sample.data.memory.size = 0

    @property
    def loaded(self):
        """Returns whether or not the sound file data is loaded in memory"""
        return self.sample.data.memory.data != NULL and self.sample.data.memory.size > 0

    @property
    def length(self):
        """Returns the length of the sound data (in bytes)"""
        if self.sample.data.memory.data == NULL:
            return 0
        else:
            return self.sample.data.memory.size


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

    def __init__(self, str file_name, int sample_rate, SDL_AudioFormat format, int channels, int buffer_size):
        # IMPORTANT: Call super class init function
        super().__init__(file_name, sample_rate, format, channels, buffer_size)

        self.sample.type = sound_type_streaming
        self.sample.data.stream = <SampleStream*>PyMem_Malloc(sizeof(SampleStream))

        self.load()

    def __dealloc__(self):
        if self.sample.data.stream != NULL:
            PyMem_Free(self.sample.data.stream)

    def __repr__(self):
        if self.sample.data.stream.pipeline == NULL:
            return '<SoundStreamingFile(Loaded=False)>'
        return '<SoundStreamingFile(Loaded=True)>'

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

        # Pipeline structure: uridecodebin --> audioconvert --> audioresample --> appsink

        # If the pipeline has already been created, delete it
        if self.pipeline != NULL:
            self._destroy_pipeline()

        # Create the pipeline
        self.pipeline = gst_pipeline_new('streaming_sound_player')
        if self.pipeline == NULL:
            raise AudioException('Unable to create a GStreamer pipeline')

        # Get the pipeline bus (the bus allows applications to receive pipeline messages)
        self.bus = gst_pipeline_get_bus(<GstPipeline*>self.pipeline)
        if self.bus == NULL:
            raise AudioException('Unable to get bus from the pipeline')

        # Enable pipeline messages and callback message handler
        gst_bus_enable_sync_message_emission(self.bus)
        self.bus_message_handler_id = c_bus_connect_message(self.bus, _on_gst_bus_message, <void*>self.audio_interface)

        # Create the urldecodebin element
        self.source = gst_element_factory_make('urldecodebin', 'source')
        if self.source == NULL:
            raise AudioException('Unable to create sound source element (urldecodebin)')

        # Create the audioconvert element
        self.convert = gst_element_factory_make('audioconvert', 'convert')
        if self.convert == NULL:
            raise AudioException('Unable to create sound converter element (audioconvert)')

        # Create the audioresample element
        self.resample = gst_element_factory_make('audioresample', 'resample')
        if self.resample == NULL:
            raise AudioException('Unable to create sound resampler element (audioresample)')

        # Create the appsink element
        self.sink = gst_element_factory_make('appsink', 'sink')
        if self.sink == NULL:
            raise AudioException('Unable to create sound resampler element (audioresample)')

        # Set appsink properties
        if SDL_AUDIO_ISLITTLEENDIAN(self.format):
            audio_format = "S16LE"
        else:
            audio_format = "S16BE"
        caps_string = 'audio/x-raw,rate={},channels={},format={},layout=interleaved'.format(
            str(self.sample_rate), str(self.channels), audio_format)

        g_object_set_caps(self.sink, caps_string.encode('utf-8'))
        g_object_set_bool(self.sink, "sync", False)
        g_object_set_int(self.sink, "blocksize", self.buffer_size)

        # Add the elements to the pipeline
        gst_bin_add(<GstBin*>self.pipeline, self.source)
        gst_bin_add(<GstBin*>self.pipeline, self.convert)
        gst_bin_add(<GstBin*>self.pipeline, self.resample)
        gst_bin_add(<GstBin*>self.pipeline, self.sink)

        # Link elements together: uridecodebin --> audioconvert --> audioresample --> appsink
        gst_element_link(self.source, self.convert)
        gst_element_link(self.convert, self.resample)
        gst_element_link(self.resample, self.sink)


    def load(self):
        """Loads the sound into memory using GStreamer"""
        cdef str pipeline_string
        cdef str file_path
        cdef GstElement *pipeline
        cdef GstElement *sink
        cdef GError *error
        cdef GstStateChangeReturn ret
        cdef GstState state
        cdef GstSample *sample
        cdef GstBuffer *buffer
        cdef GstMapInfo map_info
        cdef gboolean is_eos

        if self.loaded:
            return

        self._gst_init()

        if not os.path.isfile(self.file_name):
            raise AudioException('Could not locate file ' + self.file_name)

        # Pipeline structure: uridecodebin --> audioconvert --> audioresample --> appsink

        # Create GStreamer pipeline with the specified caps (from a string)
        file_path = 'file:///' + self.file_name.replace('\\', '/')
        if self.little_endian:
            audio_format = "S16LE"
        else:
            audio_format = "S16BE"
        pipeline_string = 'playbin uri="{}" ! appsink name=sink caps="audio/x-raw,rate={},channels={},format={},layout=interleaved" sync=false blocksize=44100'.format(
            file_path, str(self.sample_rate), str(self.channels), audio_format)

        print(pipeline_string)

        error = NULL
        pipeline = gst_parse_launch(pipeline_string.encode('utf-8'), &error)

        if error != NULL:
            msg = 'Unable to create a GStreamer pipeline: code={} message={}'.format(error.code, <bytes>error.message)
            raise AudioException(msg)

        # Get sink
        sink = gst_bin_get_by_name(<GstBin*>pipeline, "sink")

        # Set to PAUSED to make the first frame arrive in the sink
        #ret = gst_element_set_state(pipeline, GST_STATE_PAUSED)

        # get ready!
        with nogil:
            ret = gst_element_set_state(pipeline, GST_STATE_PAUSED)

        # The pipeline should now be ready to play.  Store the pointers to the pipeline
        # and appsink in the SampleStream struct for use in the application.
        self.sample.data.stream.pipeline = pipeline
        self.sample.data.stream.sink = sink


    def unload(self):
        """Unloads the sample data from memory"""
        # TODO: clean-up and destroy pipeline and associated elements (don't forget an open map)
        pass

    @property
    def loaded(self):
        """Returns whether or not the sound file data is loaded in memory"""
        return self.sample.data.stream != NULL and self.sample.data.stream.pipeline != NULL and self.sample.data.stream.sink != NULL

