#!python
#cython: embedsignature=True, language_level=3
"""
Audio Library

This library requires the SDL2, SDL_Mixer, and Gstreamer libraries.
"""


from libc.stdio cimport FILE, fopen, fprintf, sprintf, fflush
from libc.string cimport memset, memcpy
from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
cimport cpython.pycapsule as pycapsule

from math import pow
import logging

from mpfmc.core.audio.sdl2 cimport *
from mpfmc.core.audio.gstreamer cimport *
from mpfmc.core.audio.track cimport *
from mpfmc.core.audio.track_standard cimport *
from mpfmc.core.audio.track_sound_loop cimport *
from mpfmc.core.audio.sound_file cimport *
from mpfmc.core.audio.audio_exception import AudioException
from mpfmc.core.audio.playlist_controller import PlaylistController


# ---------------------------------------------------------------------------
#    Various audio engine setting values
# ---------------------------------------------------------------------------
DEF MAX_TRACKS = 8

# The maximum number of markers that can be specified for a single sound
DEF MAX_MARKERS = 16

# The number of seconds over which to perform a quick fade to avoid pops and
# clicks
DEF QUICK_FADE_DURATION_SECS = 0.05


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
    cdef list tracks
    cdef dict playlist_controllers
    cdef object mc
    cdef object log

    cdef AudioCallbackData audio_callback_data

    def __cinit__(self, *args, **kw):
        pass

    def __init__(self, rate=44100, channels=2, buffer_samples=4096):
        """
        Initializes the AudioInterface.
        Args:
            rate: The audio sample rate used in the library
            channels: The number of channels to use (1=mono, 2=stereo)
            buffer_samples: The audio buffer size to use (in number of samples, must be power of two)
        """
        self.log = logging.getLogger("AudioInterface")

        # Initialize threading in the extension library and acquire the Python global interpreter lock
        PyEval_InitThreads()

        if channels not in (1, 2):
            self.log.error('Channels is required to be either 1 (mono) or 2 (stereo)')
            raise AudioException("Unable to initialize Audio Interface: "
                                 "Channels is required to be either 1 (mono) or 2 (stereo)")

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
        if SDL_InitSubSystem(SDL_INIT_AUDIO) < 0:
            self.log.error('SDL_InitSubSystem error - %s' % SDL_GetError())
            raise AudioException('Unable to initialize SDL (SDL_InitSubSystem call failed: %s)' % SDL_GetError())

        # Initialize the SDL_Mixer library to establish the output audio format and encoding
        # (sample rate, bit depth, buffer size)
        if Mix_OpenAudio(rate, AUDIO_S16SYS, channels, buffer_samples):
            self.log.error('Mix_OpenAudio error - %s' % SDL_GetError())
            raise AudioException('Unable to open audio for output (Mix_OpenAudio failed: %s)' % SDL_GetError())

        # We want to use as little resources as possible for SDL_Mixer as we will just be using the custom
        # music player hook to play audio (no mixer channels needed).
        Mix_AllocateChannels(0)

        # Initialize GStreamer
        self._initialize_gstreamer()

        self.log.info("Initialized")
        self.log.info("Loaded %s", AudioInterface.get_sdl_version())
        self.log.info("Loaded %s", AudioInterface.get_sdl_mixer_version())
        self.log.info("Loaded %s", AudioInterface.get_gstreamer_version())
        self.log.info("Loaded %s", AudioInterface.get_glib_version())

        # Lock SDL from calling the audio callback functions while we set things up
        SDL_LockAudio()

        # Determine the actual audio format in use by the opened audio device.  This may or may not match
        # the parameters used to initialize the audio interface.
        self.audio_callback_data.buffer_samples = buffer_samples
        Mix_QuerySpec(&self.audio_callback_data.sample_rate,
                      &self.audio_callback_data.format,
                      &self.audio_callback_data.channels)

        # Ensure system is little endian (big endian not supported)
        if not SDL_AUDIO_ISLITTLEENDIAN(self.audio_callback_data.format):
            self.log.error("The audio interface only supports little endian systems in this release. "
                           "Audio features will not be available.")
            raise AudioException("The audio interface only supports little endian systems in this release.")

        # The requested values used to initialize the audio interface.  A pointer to the audio_callback_data
        # structure is passed to the SDL audio callback function and is the source of all audio state
        # and mixing data needed to generate the output signal.
        self.audio_callback_data.bytes_per_sample = SDL_AUDIO_BITSIZE(self.audio_callback_data.format) // 8
        self.audio_callback_data.buffer_size = self.audio_callback_data.buffer_samples * self.audio_callback_data.bytes_per_sample * self.audio_callback_data.channels
        self.audio_callback_data.bytes_per_control_point = self.audio_callback_data.buffer_size // CONTROL_POINTS_PER_BUFFER
        self.audio_callback_data.seconds_to_bytes_factor = self.audio_callback_data.sample_rate * self.audio_callback_data.channels * self.audio_callback_data.bytes_per_sample
        self.audio_callback_data.master_volume = SDL_MIX_MAXVOLUME // 2
        self.audio_callback_data.quick_fade_steps = (<int>(QUICK_FADE_DURATION_SECS *
                                                     self.audio_callback_data.sample_rate *
                                                     self.audio_callback_data.channels *
                                                     self.audio_callback_data.bytes_per_sample
                                                           )) // self.audio_callback_data.bytes_per_control_point
        self.audio_callback_data.silence = 0
        self.audio_callback_data.track_count = 0
        self.audio_callback_data.tracks = <void**>PyMem_Malloc(MAX_TRACKS * sizeof(TrackState*))
        self.audio_callback_data.c_log_file = NULL
        # self.audio_callback_data.c_log_file = fopen("/tmp/MPFMC_AudioLibrary.log", "wb")
        # self.audio_callback_data.c_log_file = fopen("D:\\Temp\\Dev\\MPFMC_AudioLibrary.log", "wb")
        # fprintf(self.audio_callback_data.c_log_file, "---------------------------------------------------------------------------\r\n")
        # fflush(self.audio_callback_data.c_log_file)

        self.log.info('Settings requested - rate: %d, channels: %d, buffer: %d samples',
                       rate, channels, buffer_samples)
        self.log.info('Settings in use - rate: %d, channels: %d, buffer: %d samples (%d bytes @ %d bytes per sample)',
                       self.audio_callback_data.sample_rate, self.audio_callback_data.channels,
                       self.audio_callback_data.buffer_samples, self.audio_callback_data.buffer_size,
                       self.audio_callback_data.bytes_per_sample)

        # Unlock the SDL audio callback functions
        SDL_UnlockAudio()

        self.tracks = list()
        self.playlist_controllers = dict()

    def __del__(self):
        """Shut down the audio interface and clean up allocated memory"""
        self.log.debug("Shutting down and cleaning up allocated memory...")

        # Stop audio processing (will stop all SDL callbacks)
        self.shutdown()

        self.audio_callback_data.track_count = 0
        PyMem_Free(self.audio_callback_data.tracks)
        self.audio_callback_data.tracks = NULL

        # Remove tracks
        self.tracks.clear()

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
        SDL_LockAudio()
        self.audio_callback_data.master_volume = <Uint8>min(max(volume * SDL_MIX_MAXVOLUME, 0), SDL_MIX_MAXVOLUME)
        SDL_UnlockAudio()

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
                    'buffer_size': self.audio_callback_data.buffer_size,
                    'bytes_per_sample': self.audio_callback_data.bytes_per_sample,
                    'seconds_to_bytes_factor': self.audio_callback_data.seconds_to_bytes_factor
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
        return Mix_GetMusicHookData() != NULL

    def enable(self):
        """
        Enables audio playback (begins audio processing)
        """
        self.log.info("Enabling audio playback")
        Mix_HookMusic(self.audio_callback, &self.audio_callback_data)

    def disable(self):
        """
        Disables audio playback (stops audio processing)
        """
        self.log.info("Disabling audio playback")
        self.stop_all_sounds()
        Mix_HookMusic(NULL, NULL)

    def shutdown(self):
        """
        Shuts down the audio device
        """
        self.disable()
        Mix_CloseAudio()

    @staticmethod
    def get_max_tracks():
        """ Returns the maximum number of tracks allowed. """
        return MAX_TRACKS

    @staticmethod
    def get_max_markers():
        """Return the maximum number of markers allowed per sound"""
        return MAX_MARKERS

    def get_track_count(self):
        """Returns the number of tracks that have been created."""
        return len(self.tracks)

    def get_track_names(self):
        """Return the list of names of tracks that have been created."""
        return [track.name for track in self.tracks]

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

    def get_track_type(self, str name not None):
        """
        Returns the type of the track with the specified name.
        Args:
            name: The name of the track
        """
        track = self.get_track_by_name(name)
        if track:
            return track.type
        else:
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
        SDL_LockAudio()

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
        SDL_UnlockAudio()

        self.log.debug("The '%s' standard track has successfully been created.", name)

        return new_track

    def create_sound_loop_track(self, object mc, str name not None,
                                int max_layers=8,
                                float volume=1.0):
        """
        Creates a new sound loop track in the audio interface
        Args:
            mc: The media controller app
            name: The name of the new track
            max_layers: The maximum number of sounds that may be played at one time on the track
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
        SDL_LockAudio()

        # Create the new live loop track
        new_track = TrackSoundLoop(mc,
                                   pycapsule.PyCapsule_New(&self.audio_callback_data, NULL, NULL),
                                   name,
                                   track_num,
                                   self.audio_callback_data.buffer_size,
                                   max_layers,
                                   volume)
        self.tracks.append(new_track)

        # Update audio callback data with new track
        self.audio_callback_data.track_count = len(self.tracks)
        self.audio_callback_data.tracks[track_num] = new_track.state

        # Allow audio callback function to be called again
        SDL_UnlockAudio()

        self.log.debug("The '%s' live loop track has successfully been created.", name)

        return new_track

    def create_playlist_track(self, object mc, str name not None, float crossfade_time=0.0, float volume=1.0):
        """
        Creates a new playlist track in the audio interface
        Args:
            mc: The media controller app
            name: The name of the new track
            crossfade_time: The default crossfade time (secs) to use when fading between sounds
            volume: The track volume (0.0 to 1.0)

        Returns:
            A Track object for the newly created track

        Notes:
            There is no specialized playlist track type.  This function creates a standard
            audio track AND a corresponding playlist controller that will be used to manage
            all sound actions on the track.
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
        SDL_LockAudio()

        # Create the new standard track
        new_track = TrackStandard(mc,
                                  pycapsule.PyCapsule_New(&self.audio_callback_data, NULL, NULL),
                                  name,
                                  track_num,
                                  self.audio_callback_data.buffer_size,
                                  2,
                                  volume)
        self.tracks.append(new_track)

        # Update audio callback data with new track
        self.audio_callback_data.track_count = len(self.tracks)
        self.audio_callback_data.tracks[track_num] = new_track.state

        # Allow audio callback function to be called again
        SDL_UnlockAudio()

        # Create playlist controller for the track
        playlist_controller = PlaylistController(mc, new_track, crossfade_time)
        self.playlist_controllers[name] = playlist_controller

        self.log.debug("The '%s' playlist track and controller have successfully been created.", name)

        return new_track

    def get_playlist_controller_count(self):
        """Returns the number of playlist controllers that have been created."""
        return len(self.playlist_controllers)

    def get_playlist_controller_names(self):
        """Return the list of names of the playlist controllers that have been created."""
        return [controller for controller in self.playlist_controllers.keys()]

    def get_playlist_controller(self, str controller_name):
        """
        Returns the playlist controller with the specified name.
        Args:
            controller_name: The playlist controller name to retrieve
        """
        try:
            return self.playlist_controllers[controller_name]
        except KeyError:
            return None

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

    def stop_all_sounds(self, float fade_out_seconds = 0.0):
        """Stops all playing and pending sounds in all tracks"""
        for track in self.tracks:
            track.stop_all_sounds(fade_out_seconds)

    def stop_sound_instance(self, sound_instance not None, fade_out=None):
        """Stops the specified sound instance"""
        for track in self.tracks:
            if hasattr(track, "stop_sound_instance"):
                track.stop_sound_instance(sound_instance, fade_out)

    def stop_sound(self, sound not None, fade_out=None):
        """Stops all instances of the specified sound on all tracks"""
        for track in self.tracks:
            if hasattr(track, "stop_sound"):
                track.stop_sound(sound, fade_out)

    def stop_sound(self, sound not None):
        """Stops all instances of the specified sound from continuing to loop on all tracks"""
        for track in self.tracks:
            if hasattr(track, "stop_sound_looping"):
                track.stop_sound_looping(sound)

    def stop_sound_instance_looping(self, sound_instance not None):
        """Stops the specified sound instance from continuing to loop."""
        for track in self.tracks:
            if hasattr(track, "stop_sound_instance_looping"):
                track.stop_sound_instance_looping(sound_instance)

    def clear_context(self, context):
        """Clears the context in all tracks"""
        for track in self.tracks:
            track.clear_context(context)

    def process(self):
        """Process tick function for the audio interface."""
        for track in self.tracks:
            track.process()

    @staticmethod
    cdef void audio_callback(void* data, Uint8 *output_buffer, int length) nogil:
        """
        Main audio callback function (called from SDL_mixer).
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
        # to debug logic errors can occur when these track loops are combined.

        # Loop over tracks, initializing the status, track buffer, and track ducking.
        for track_num in range(callback_data.track_count):
            track = <TrackState*>callback_data.tracks[track_num]

            track.active = False
            memset(track.buffer, 0, buffer_length)

            track.ducking_is_active = False
            for control_point in range(CONTROL_POINTS_PER_BUFFER):
                g_array_set_val_uint8(track.ducking_control_points, control_point, SDL_MIX_MAXVOLUME)

        # Loop over tracks, mixing the playing sounds into the track's audio buffer
        for track_num in range(callback_data.track_count):
            track = <TrackState*>callback_data.tracks[track_num]

            # No need to process/mix the track if the track is stopped or paused
            if track.status == track_status_stopped or track.status == track_status_paused:
                continue

            # Call the track's mix callback function (generates audio into track buffer)
            if track.mix_callback_function != NULL:
                track.mix_callback_function(track, buffer_length, callback_data)

        # Loop over tracks again, applying ducking and mixing down tracks to the master output buffer
        for track_num in range(callback_data.track_count):
            track = <TrackState*>callback_data.tracks[track_num]

            # Only mix the track to the master output and apply ducking if it is active
            if track.active:
                Track.mix_track_to_output(track,
                                          callback_data,
                                          output_buffer,
                                          buffer_length)

        # Apply master volume to output buffer
        Track.apply_volume(output_buffer, output_buffer, buffer_length, callback_data.master_volume)
