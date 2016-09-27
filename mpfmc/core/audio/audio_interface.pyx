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

__version_info__ = ('0', '31', '1')
__version__ = '.'.join(__version_info__)

from libc.stdio cimport FILE, fopen, fprintf
from libc.stdlib cimport malloc, free, calloc
from libc.string cimport memset, memcpy
from cpython.mem cimport PyMem_Malloc, PyMem_Free
cimport cpython.pycapsule as pycapsule
import cython

from queue import PriorityQueue, Empty
from math import pow
import time
import logging


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
#    AudioInterface class
# ---------------------------------------------------------------------------
cdef class AudioInterface:
    """
    The AudioInterface class provides a management wrapper around the SDL2 and SDL_Mixer
    libraries.
    """
    cdef public int sample_rate
    cdef int audio_channels
    cdef int buffer_samples
    cdef int buffer_size
    cdef int supported_formats
    cdef list tracks
    cdef object mc
    cdef object log
    cdef dict sound_instances_by_id

    cdef AudioCallbackData *audio_callback_data

    def __cinit__(self, *args, **kw):
        self.sample_rate = 0
        self.audio_channels = 0
        self.buffer_samples = 0
        self.buffer_size = 0
        self.supported_formats = 0
        self.audio_callback_data = NULL

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

        # Initialize the SDL_Mixer library to establish the output audio format and encoding
        # (sample rate, bit depth, buffer size)
        if Mix_OpenAudio(rate, AUDIO_S16SYS, channels, buffer_samples):
            self.log.error('Mix_OpenAudio error - %s' % SDL_GetError())
            raise AudioException('Unable to open audio for output (Mix_OpenAudio failed: %s)' % SDL_GetError())

        self.log.info("Initialized %s", AudioInterface.get_version())
        self.log.debug("Loaded %s", AudioInterface.get_sdl_version())
        self.log.debug("Loaded %s", AudioInterface.get_sdl_mixer_version())

        # Lock SDL from calling the audio callback functions
        SDL_LockAudio()

        # Determine the actual audio format in use by the opened audio device.  This may or may not match
        # the parameters used to initialize the audio interface.
        self.buffer_samples = buffer_samples
        self.log.debug('Settings requested - rate: %d, channels: %d, buffer: %d samples',
                       rate, channels, buffer_samples)
        Mix_QuerySpec(&self.sample_rate, NULL, &self.audio_channels)
        self.log.debug('Settings in use - rate: %d, channels: %d, buffer: %d samples',
                       self.sample_rate, self.audio_channels, self.buffer_samples)

        # Set the size of the track audio buffers (samples * channels * size of 16-bit int) for 16-bit audio
        self.buffer_size = self.buffer_samples * self.audio_channels * sizeof(Uint16)

        # Allocate memory for the audio callback data structure
        self.audio_callback_data = <AudioCallbackData*> PyMem_Malloc(sizeof(AudioCallbackData))

        # Initialize the audio callback data structure
        self.audio_callback_data.sample_rate = self.sample_rate
        self.audio_callback_data.audio_channels = self.audio_channels
        self.audio_callback_data.buffer_size = self.buffer_size
        self.audio_callback_data.master_volume = MIX_MAX_VOLUME // 2
        self.audio_callback_data.track_count = 0
        self.audio_callback_data.tracks = <TrackState**> PyMem_Malloc(MAX_TRACKS * sizeof(TrackState*))
        self.audio_callback_data.c_log_file = NULL
        #self.audio_callback_data.c_log_file = fopen("D:\\Temp\\Dev\\MPFMC_AudioLibrary.log", "wb")

        # Initialize request messages
        self.audio_callback_data.request_messages = <RequestMessageContainer**> PyMem_Malloc(
            MAX_REQUEST_MESSAGES * sizeof(RequestMessageContainer*))

        for i in range(MAX_REQUEST_MESSAGES):
            self.audio_callback_data.request_messages[i] = <RequestMessageContainer*> PyMem_Malloc(sizeof(RequestMessageContainer))
            self.audio_callback_data.request_messages[i].message = request_not_in_use
            self.audio_callback_data.request_messages[i].sound_id = 0
            self.audio_callback_data.request_messages[i].sound_instance_id = 0
            self.audio_callback_data.request_messages[i].track = 0
            self.audio_callback_data.request_messages[i].player = 0
            self.audio_callback_data.request_messages[i].time = 0

        # Initialize notification messages
        self.audio_callback_data.notification_messages = <NotificationMessageContainer**> PyMem_Malloc(
            MAX_NOTIFICATION_MESSAGES * sizeof(NotificationMessageContainer*))

        for i in range(MAX_REQUEST_MESSAGES):
            self.audio_callback_data.notification_messages[i] = <NotificationMessageContainer*> PyMem_Malloc(sizeof(NotificationMessageContainer))
            self.audio_callback_data.notification_messages[i].message = notification_not_in_use
            self.audio_callback_data.notification_messages[i].sound_id = 0
            self.audio_callback_data.notification_messages[i].sound_instance_id = 0
            self.audio_callback_data.notification_messages[i].track = 0
            self.audio_callback_data.notification_messages[i].player = 0
            self.audio_callback_data.notification_messages[i].time = 0

        self.audio_callback_data.mutex = SDL_CreateMutex()

        # Initialize the supported SDL_Mixer library formats
        self.supported_formats = Mix_Init(MIX_INIT_OGG)

        # Unlock the SDL audio callback functions
        SDL_UnlockAudio()

        self.tracks = list()
        self.sound_instances_by_id = dict()

    def __del__(self):
        """Shut down the audio interface and clean up allocated memory"""
        self.log.debug("Shutting down and cleaning up allocated memory...")

        # Stop audio processing (will stop all SDL callbacks)
        self.disable()

        # Remove tracks
        self.tracks.clear()

        # Free all allocated memory
        for i in range(MAX_REQUEST_MESSAGES):
            PyMem_Free(self.audio_callback_data.request_messages[i])
        for i in range(MAX_NOTIFICATION_MESSAGES):
            PyMem_Free(self.audio_callback_data.notification_messages[i])

        PyMem_Free(self.audio_callback_data.request_messages)
        PyMem_Free(self.audio_callback_data.notification_messages)

        PyMem_Free(self.audio_callback_data.tracks)
        SDL_DestroyMutex(self.audio_callback_data.mutex)
        PyMem_Free(self.audio_callback_data)

        # SDL_Mixer no longer needed
        Mix_Quit()
        SDL_Quit()

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
        return int(self.sample_rate * seconds)

    def convert_seconds_to_buffer_length(self, float seconds):
        """Convert the specified number of seconds into a buffer length (based on current
        sample rate, the number of audio channels, and the number of bytes per sample)."""
        return int(seconds * self.sample_rate * self.audio_channels * BYTES_PER_SAMPLE)

    def convert_buffer_length_to_seconds(self, int buffer_length):
        """Convert the specified buffer length into a time in seconds (based on current
        sample rate, the number of audio channels, and the number of bytes per sample)."""
        return round(buffer_length / (self.sample_rate * self.audio_channels * BYTES_PER_SAMPLE), 3)

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
        return int(self.sample_rate * seconds)

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
    def get_sdl_mixer_version(cls):
        """
        Returns the version of the dynamically linked SDL_Mixer library
        :return: SDL_Mixer library version string
        """
        cdef const SDL_version *version = Mix_Linked_Version()
        return 'SDL_Mixer {}.{}.{}'.format(version.major, version.minor, version.patch)

    def supported_extensions(self):
        """
        Get the file extensions that are supported by the audio interface.
        Returns:
            A list of file extensions supported.
        """
        extensions = ["wav"]
        if self.supported_formats & MIX_INIT_FLAC:
            extensions.append("flac")
        if self.supported_formats & MIX_INIT_OGG:
            extensions.append("ogg")
        return extensions

    def get_master_volume(self):
        return round(self.audio_callback_data.master_volume / MIX_MAX_VOLUME, 2)

    def set_master_volume(self, float volume):
        SDL_LockMutex(self.audio_callback_data.mutex)
        self.audio_callback_data.master_volume = <Uint8>min(max(volume * MIX_MAX_VOLUME, 0), MIX_MAX_VOLUME)
        SDL_UnlockMutex(self.audio_callback_data.mutex)

    def get_settings(self):
        """
        Gets the current audio interface settings. This method is only intended for testing purposes.
        Returns:
            A dictionary containing the current audio interface settings or None if the
            audio interface is not enabled.
        """
        if self.enabled:
            return {'sample_rate': self.sample_rate,
                    'audio_channels': self.audio_channels,
                    'buffer_samples': self.buffer_samples,
                    'buffer_size': self.buffer_size
                    }
        else:
            return None

    @property
    def enabled(self):
        cdef void *data
        SDL_LockAudio()
        data = Mix_GetMusicHookData()
        SDL_UnlockAudio()
        return data != NULL

    def enable(self):
        """
        Enables audio playback (begins audio processing)
        """
        self.log.debug("Enabling audio playback")

        SDL_LockAudio()
        # Establish custom music hook/callback function
        Mix_HookMusic(AudioInterface.audio_callback, <void*>self.audio_callback_data)
        SDL_UnlockAudio()

    def disable(self):
        """
        Disables audio playback (stops audio processing)
        """
        self.log.debug("Disabling audio playback")

        self.stop_all_sounds()

        SDL_LockAudio()
        # Remove custom music hook/callback function
        Mix_HookMusic(NULL, NULL)
        SDL_UnlockAudio()

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

    def create_standard_track(self, str name not None,
                              int max_simultaneous_sounds=MAX_SIMULTANEOUS_SOUNDS_DEFAULT,
                              float volume=1.0):
        """
        Creates a new standard track in the audio interface
        Args:
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
        new_track = TrackStandard(self.sound_instances_by_id,
                                  pycapsule.PyCapsule_New(self.audio_callback_data, NULL, NULL),
                                  name,
                                  track_num,
                                  self.buffer_size,
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

    def create_live_loop_track(self, str name not None, float volume=1.0):
        """
        Creates a new live loop track in the audio interface
        Args:
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
        SDL_LockAudio()

        # Create the new live loop track
        new_track = TrackLiveLoop(self.mc,
                                  pycapsule.PyCapsule_New(self.audio_callback_data, NULL, NULL),
                                  name,
                                  track_num,
                                  self.buffer_size,
                                  volume)
        self.tracks.append(new_track)

        # Update audio callback data with new track
        self.audio_callback_data.track_count = len(self.tracks)
        self.audio_callback_data.tracks[track_num] = new_track.state

        # Allow audio callback function to be called again
        SDL_UnlockAudio()

        self.log.debug("The '%s' live loop track has successfully been created.", name)

        return new_track

    @staticmethod
    def load_sound_chunk(str file_name):
        """
        Loads an audio file into a MixChunkContainer wrapper object for use in a Sound object.
        Used in asset loading for Sound objects.
        Args:
            file_name: The audio file name to load.

        Returns:
            A MixChunkContainer wrapper object containing a pointer to the sound sample
            in memory.  None is returned if the sound file was unable to be loaded.
        """
        # String conversion from Python to char* (it takes a few steps)
        # See http://docs.cython.org/src/tutorial/strings.html for more information.
        # 1) convert the python string (str) to a byte string (use UTF-8 encoding)
        # 2) convert the python byte string to a C char* (can just do an assign)
        # 3) the C char* string is now ready for use in calls to the C library
        py_byte_file_name = file_name.encode('UTF-8')
        cdef char *c_file_name = py_byte_file_name

        # Attempt to load the file
        cdef Mix_Chunk *chunk = Mix_LoadWAV(c_file_name)
        if chunk == NULL:
            raise AudioException("Unable to load sound from source file '{}' - {}"
                                 .format(file_name, SDL_GetError()))

        # Create a Python container object to wrap the Mix_Chunk C pointer
        cdef MixChunkContainer mc = MixChunkContainer()
        mc.chunk = chunk
        return mc

    @staticmethod
    def unload_sound_chunk(container):
        """
        Unloads the source sample (Mix_Chunk) from the supplied container (used in Sound
        asset unloading).  The sound will no longer be in memory.
        Args:
            container: A MixChunkContainer object
        """
        if not isinstance(container, MixChunkContainer):
            return

        cdef MixChunkContainer mc = container
        if mc.chunk != NULL:
            SDL_LockAudio()
            Mix_FreeChunk(mc.chunk)
            SDL_UnlockAudio()
            mc.chunk = NULL

    def stop_sound(self, sound_instance not None):
        """
        Stops all instances of the specified sound immediately on all tracks.
        Args:
            sound_instance: The SoundInstance to stop
        """
        for track in self.tracks:
            track.stop_sound(sound_instance)

    def stop_all_sounds(self):
        """Stops all playing and pending sounds in all tracks"""
        for track in self.tracks:
            track.stop_all_sounds()

    def process(self):
        """Process tick function for the audio interface."""

        # Process tracks
        for track in self.tracks:
            track.process()

        # Process any internal notification messages that may cause other messages to be generated
        SDL_LockMutex(self.audio_callback_data.mutex)
        for message_num in range(MAX_NOTIFICATION_MESSAGES):
            if self.audio_callback_data.notification_messages[message_num].message != notification_not_in_use:
                # Dispatch message processing to target track
                track = self.get_track(self.audio_callback_data.notification_messages[message_num].track)
                if track is not None:
                    track.process_notification_message(message_num)

        SDL_UnlockMutex(self.audio_callback_data.mutex)

    def get_in_use_request_message_count(self):
        """
        Returns the number of request messages currently in use.  Used for debugging and testing.
        """
        in_use_message_count = 0
        SDL_LockMutex(self.audio_callback_data.mutex)
        for message_num in range(MAX_REQUEST_MESSAGES):
            if self.audio_callback_data.request_messages[message_num].message != request_not_in_use:
                in_use_message_count += 1

        SDL_UnlockMutex(self.audio_callback_data.mutex)
        return in_use_message_count

    def get_in_use_notification_message_count(self):
        """
        Returns the number of notification messages currently in use.  Used for debugging and testing.
        """
        in_use_message_count = 0
        SDL_LockMutex(self.audio_callback_data.mutex)
        for message_num in range(MAX_NOTIFICATION_MESSAGES):
            if self.audio_callback_data.notification_messages[message_num].message != notification_not_in_use:
                in_use_message_count += 1

        SDL_UnlockMutex(self.audio_callback_data.mutex)
        return in_use_message_count

    @staticmethod
    cdef void audio_callback(void* data, Uint8 *output_buffer, int length) nogil:
        """
        Main audio callback function (called from SDL_Mixer).
        Args:
            data: A pointer to the AudioCallbackData class for the channel (contains all audio
                processing-related settings and state, ex: interface settings, tracks, sound
                players, ducking envelopes, etc.)
            output_buffer: The music audio buffer for SDL_Mixer to process
            length: The length (bytes) of the audio buffer

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

        # Initialize master output buffer (silence)
        memset(output_buffer, 0, buffer_length)

        # Lock the mutex to ensure no audio data is changed during the playback processing
        # (multi-threaded protection)
        SDL_LockMutex(callback_data.mutex)

        # Note: There are three separate loops over the tracks that must remain separate due
        # to various track parameters than can be set for any track during each loop.  Difficult
        # to debug logic errors will occur if these track loops are combined.

        # Loop over tracks, initializing the track buffer and status.
        for track_num in range(callback_data.track_count):
            callback_data.tracks[track_num].active = False
            callback_data.tracks[track_num].ducking_is_active = False
            memset(callback_data.tracks[track_num].buffer, 0, buffer_length)

        # Process any internal sound messages that may affect sound playback (play and stop messages)
        process_request_messages(callback_data)

        # Loop over tracks, mixing the playing sounds into the track's audio buffer
        for track_num in range(callback_data.track_count):
            track = callback_data.tracks[track_num]

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
                mix_track_to_output(<Uint8*> callback_data.tracks[track_num].buffer,
                                    callback_data.tracks[track_num].volume,
                                    output_buffer,
                                    buffer_length)

        # Apply master volume to output buffer
        apply_volume_to_buffer(output_buffer, buffer_length, callback_data.master_volume)

        # Unlock the mutex since we are done accessing the audio data
        SDL_UnlockMutex(callback_data.mutex)

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
    Processes any new sound messages that should be processed prior to the main
    audio callback processing (such as sound play and sound stop messages).
    Args:
        callback_data: The audio callback data structure
    """
    cdef int i, track_num
    cdef TrackState *track

    # Loop over messages
    for i in range(MAX_REQUEST_MESSAGES):

        # Dispatch messages to recipient track's request message processing function
        if callback_data.request_messages[i].message != request_not_in_use:
            track_num = callback_data.request_messages[i].track
            track = callback_data.tracks[track_num]
            if track.type == track_type_standard:
                process_standard_track_request_message(callback_data.request_messages[i], track)
            elif track.type == track_type_playlist:
                # TODO: Implement track request message function call
                pass
            elif track.type == track_type_live_loop:
                # process_live_loop_request_message(callback_data.request_messages[i], track)
                # TODO: Implement track request message function call
                pass

cdef void process_standard_track_request_message(RequestMessageContainer *request_message,
                                                 TrackState *track) nogil:
    """
    Processes any new standard track request messages that should be processed prior to the
    main audio callback processing (such as sound play and sound stop messages).
    Args:
        request_message: The request message to process
        track: The TrackState struct for this track
    """
    cdef int player = request_message.player
    cdef TrackStandardState *standard_track

    if track.type != track_type_standard or track.type_state == NULL:
        return

    standard_track = <TrackStandardState*>track.type_state

    if request_message.message == request_sound_play:
        # Update player to start playing new sound
        standard_track.sound_players[player].status = player_pending
        standard_track.sound_players[player].current.sample_pos = request_message.data.play.start_at_position
        standard_track.sound_players[player].current.current_loop = 0
        standard_track.sound_players[player].current.sound_id = request_message.sound_id
        standard_track.sound_players[player].current.sound_instance_id = request_message.sound_instance_id
        standard_track.sound_players[player].current.chunk = request_message.data.play.chunk
        standard_track.sound_players[player].current.volume = request_message.data.play.volume
        standard_track.sound_players[player].current.loops_remaining = request_message.data.play.loops
        standard_track.sound_players[player].current.sound_priority = request_message.data.play.priority

        # Fading (done at control rate; need to calculate the number of steps over which to fade in/out)
        standard_track.sound_players[player].current.fade_in_steps = request_message.data.play.fade_in_duration // (track.buffer_size // CONTROL_POINTS_PER_BUFFER)
        standard_track.sound_players[player].current.fade_out_steps = request_message.data.play.fade_out_duration // (track.buffer_size // CONTROL_POINTS_PER_BUFFER)
        standard_track.sound_players[player].current.fade_steps_remaining = standard_track.sound_players[player].current.fade_in_steps
        if standard_track.sound_players[player].current.fade_steps_remaining > 0:
            standard_track.sound_players[player].current.fading_status = fading_status_fading_in
        else:
            standard_track.sound_players[player].current.fading_status = fading_status_not_fading

        # Markers
        standard_track.sound_players[player].current.marker_count = request_message.data.play.marker_count

        for index in range(request_message.data.play.marker_count):
            standard_track.sound_players[player].current.markers[index] = request_message.data.play.markers[index]

        if request_message.data.play.sound_has_ducking:
            standard_track.sound_players[player].current.sound_has_ducking = True
            standard_track.sound_players[player].current.ducking_settings.track_bit_mask = request_message.data.play.ducking_settings.track_bit_mask
            standard_track.sound_players[player].current.ducking_settings.attack_start_pos = request_message.data.play.ducking_settings.attack_start_pos
            standard_track.sound_players[player].current.ducking_settings.attack_duration = request_message.data.play.ducking_settings.attack_duration
            standard_track.sound_players[player].current.ducking_settings.attenuation_volume = request_message.data.play.ducking_settings.attenuation_volume
            standard_track.sound_players[player].current.ducking_settings.release_start_pos = request_message.data.play.ducking_settings.release_start_pos
            standard_track.sound_players[player].current.ducking_settings.release_duration = request_message.data.play.ducking_settings.release_duration
            standard_track.sound_players[player].current.ducking_stage = ducking_stage_delay

        else:
            standard_track.sound_players[player].current.sound_has_ducking = False

        # Clear request message since it has been processed
        request_message.message = request_not_in_use

    elif request_message.message == request_sound_stop:
        # Update player to stop playing sound
        standard_track.sound_players[player].status = player_stopping

        # Calculate fade out (if necessary)
        standard_track.sound_players[player].current.fade_steps_remaining = request_message.data.stop.fade_out_duration // (track.buffer_size // CONTROL_POINTS_PER_BUFFER)
        if standard_track.sound_players[player].current.fade_steps_remaining > 0:
            standard_track.sound_players[player].current.fade_out_steps = standard_track.sound_players[player].current.fade_steps_remaining
            standard_track.sound_players[player].current.fading_status = fading_status_fading_out
        else:
            standard_track.sound_players[player].current.fading_status = fading_status_not_fading

        # Adjust ducking release (if necessary)
        if standard_track.sound_players[player].current.sound_has_ducking:
            # standard_track.sound_players[player].current.ducking_settings.release_duration = request_message.data.stop.ducking_release_duration
            # standard_track.sound_players[player].current.ducking_settings.release_start_pos = standard_track.sound_players[player].current.sample_pos
            # TODO: Add more intelligent ducking release point calculation here:
            #       Take into consideration whether ducking is already in progress and when it was
            #       originally scheduled to finish.
            pass

        # Clear request message since it has been processed
        request_message.message = request_not_in_use

    elif request_message.message == request_sound_replace:
        # Update player to stop playing current sound and start playing new sound
        standard_track.sound_players[player].status = player_replacing
        standard_track.sound_players[player].next.sample_pos = request_message.data.play.start_at_position
        standard_track.sound_players[player].next.current_loop = 0
        standard_track.sound_players[player].next.sound_id = request_message.sound_id
        standard_track.sound_players[player].next.sound_instance_id = request_message.sound_instance_id
        standard_track.sound_players[player].next.chunk = request_message.data.play.chunk
        standard_track.sound_players[player].next.volume = request_message.data.play.volume
        standard_track.sound_players[player].next.loops_remaining = request_message.data.play.loops
        standard_track.sound_players[player].next.sound_priority = request_message.data.play.priority

        # Fading (done at control rate; need to calculate the number of steps over which to fade in/out)
        standard_track.sound_players[player].next.fade_in_steps = request_message.data.play.fade_in_duration // (track.buffer_size // CONTROL_POINTS_PER_BUFFER)
        standard_track.sound_players[player].next.fade_out_steps = request_message.data.play.fade_out_duration // (track.buffer_size // CONTROL_POINTS_PER_BUFFER)
        standard_track.sound_players[player].next.fade_steps_remaining = standard_track.sound_players[player].next.fade_in_steps
        if standard_track.sound_players[player].next.fade_steps_remaining > 0:
            standard_track.sound_players[player].next.fading_status = fading_status_fading_in
        else:
            standard_track.sound_players[player].next.fading_status = fading_status_not_fading

        # Markers
        standard_track.sound_players[player].next.marker_count = request_message.data.play.marker_count

        for index in range(request_message.data.play.marker_count):
            standard_track.sound_players[player].next.markers[index] = request_message.data.play.markers[index]

        if request_message.data.play.sound_has_ducking:
            standard_track.sound_players[player].next.sound_has_ducking = True
            standard_track.sound_players[player].next.ducking_settings.track_bit_mask = request_message.data.play.ducking_settings.track_bit_mask
            standard_track.sound_players[player].next.ducking_settings.attack_start_pos = request_message.data.play.ducking_settings.attack_start_pos
            standard_track.sound_players[player].next.ducking_settings.attack_duration = request_message.data.play.ducking_settings.attack_duration
            standard_track.sound_players[player].next.ducking_settings.attenuation_volume = request_message.data.play.ducking_settings.attenuation_volume
            standard_track.sound_players[player].next.ducking_settings.release_start_pos = request_message.data.play.ducking_settings.release_start_pos
            standard_track.sound_players[player].next.ducking_settings.release_duration = request_message.data.play.ducking_settings.release_duration
            standard_track.sound_players[player].next.ducking_stage = ducking_stage_delay

        else:
            standard_track.sound_players[player].next.sound_has_ducking = False

        # TODO: Figure out how to handle ducking when replacing an existing sound

        # Clear request message since it has been processed
        request_message.message = request_not_in_use

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

    if track == NULL or track.type != track_type_standard:
        return

    # Get the current clock from SDL (it is used for the audio timing master)
    cdef Uint32 sdl_ticks = SDL_GetTicks()

    # Setup source (sound) and destination (track) buffer pointers/values
    cdef Uint8 *sound_buffer
    cdef Uint8 *output_buffer = <Uint8*> track.buffer

    cdef int message_index
    cdef Uint32 buffer_pos
    cdef Uint32 fade_out_duration
    cdef Uint32 sound_samples_remaining
    cdef Uint8 volume

    cdef Uint32 samples_per_control_point
    cdef Uint32 control_point_pos
    cdef bint ducking_is_active
    cdef float progress
    cdef int track_num
    cdef int marker_id

    standard_track = <TrackStandardState*>track.type_state
    samples_per_control_point = buffer_length // CONTROL_POINTS_PER_BUFFER

    # Loop over track sound players
    for player in range(standard_track.sound_player_count):

        # If the player is idle, there is nothing to do so move on to the next player
        if standard_track.sound_players[player].status is player_idle \
                or standard_track.sound_players[player].current.chunk == NULL:
            continue

        buffer_pos = 0
        track.active = True

        # Get source sound buffer (read one byte at a time, bytes will be combined into a
        # 16-bit sample value before being mixed)
        sound_buffer = <Uint8*> standard_track.sound_players[player].current.chunk.abuf

        # Check if player has been requested to stop a sound
        if standard_track.sound_players[player].status is player_stopping:

            if standard_track.sound_players[player].current.sound_has_ducking:
                # Initiate a fast ducking release (10 ms)
                # TODO: implement ducking release here
                pass

            volume = standard_track.sound_players[player].current.volume

            # Loop over destination buffer, mixing in the source sample
            while buffer_pos < buffer_length:

                # Calculate volume at the control rate (handle fading)
                if (buffer_pos % samples_per_control_point) == 0:
                    if standard_track.sound_players[player].current.fading_status == fading_status_fading_out:
                        volume = <Uint8> (in_out_quad(standard_track.sound_players[player].current.fade_steps_remaining /
                            standard_track.sound_players[player].current.fade_out_steps) * standard_track.sound_players[
                                              player].current.volume)
                        standard_track.sound_players[player].current.fade_steps_remaining -= 1
                        if standard_track.sound_players[player].current.fade_steps_remaining == 0:
                            standard_track.sound_players[player].current.fading_status = fading_status_not_fading
                            standard_track.sound_players[player].status = player_finished
                    else:
                        volume = standard_track.sound_players[player].current.volume
                        standard_track.sound_players[player].status = player_finished

                mix_sound_sample_to_buffer(sound_buffer,
                                           standard_track.sound_players[player].current.sample_pos,
                                           volume,
                                           output_buffer,
                                           buffer_pos)

                # Advance the source sample pointer to the next sample
                standard_track.sound_players[player].current.sample_pos += BYTES_PER_SAMPLE

                # Advance the output buffer pointer to the next sample
                buffer_pos += BYTES_PER_SAMPLE

                # Check if we are at the end of the source sample buffer
                if standard_track.sound_players[player].current.sample_pos >= standard_track.sound_players[player].current.chunk.alen:
                    end_of_sound_processing(cython.address(standard_track.sound_players[player]),
                                            callback_data.notification_messages, sdl_ticks)

                if standard_track.sound_players[player].status is player_finished:
                    break

        # Check if player has been requested to stop a sound and immediately replace it with another sound
        if standard_track.sound_players[player].status is player_replacing:

            sound_samples_remaining = standard_track.sound_players[player].current.chunk.alen - standard_track.sound_players[
                player].current.sample_pos
            fade_out_duration = min(buffer_length,
                                    <Uint32>(callback_data.sample_rate * callback_data.audio_channels *
                                          QUICK_FADE_DURATION_SECS),
                                    sound_samples_remaining)
            volume = standard_track.sound_players[player].current.volume

            if standard_track.sound_players[player].current.sound_has_ducking:
                # Initiate a fast ducking release (10 ms)
                # TODO: implement ducking release here
                pass

            # Loop over destination buffer, mixing in the source sample
            while buffer_pos < fade_out_duration:
                mix_sound_sample_to_buffer(sound_buffer,
                                           standard_track.sound_players[player].current.sample_pos,
                                           volume,
                                           output_buffer,
                                           buffer_pos)

                # Advance the source sample pointer to the next sample (2 bytes)
                standard_track.sound_players[player].current.sample_pos += BYTES_PER_SAMPLE

                # Advance the output buffer pointer to the next sample (2 bytes)
                buffer_pos += BYTES_PER_SAMPLE

                # Check if we are at the end of the source sample buffer (loop if applicable)
                if standard_track.sound_players[player].current.sample_pos >= standard_track.sound_players[player].current.chunk.alen:
                    end_of_sound_processing(cython.address(standard_track.sound_players[player]),
                                            callback_data.notification_messages, sdl_ticks)
                    if standard_track.sound_players[player].status is player_finished:
                        break

                # Set volume for next loop
                volume = <int> (
                    (1.0 - in_out_quad(buffer_pos / fade_out_duration)) * standard_track.sound_players[player].current.volume)

            # Send audio event that the sound has stopped
            send_sound_stopped_notification(track.number, player,
                                     standard_track.sound_players[player].current.sound_id,
                                     standard_track.sound_players[player].current.sound_instance_id,
                                     callback_data.notification_messages,
                                     sdl_ticks)

            # Update sound player status to finished
            standard_track.sound_players[player].status = player_pending

            # Copy sound player settings from next sound to current
            standard_track.sound_players[player].status = player_pending
            standard_track.sound_players[player].current.sample_pos = standard_track.sound_players[player].next.sample_pos
            standard_track.sound_players[player].current.current_loop = standard_track.sound_players[player].next.current_loop
            standard_track.sound_players[player].current.sound_id = standard_track.sound_players[player].next.sound_id
            standard_track.sound_players[player].current.sound_instance_id = standard_track.sound_players[player].next.sound_instance_id
            standard_track.sound_players[player].current.chunk = standard_track.sound_players[player].next.chunk
            standard_track.sound_players[player].current.volume = standard_track.sound_players[player].next.volume
            standard_track.sound_players[player].current.loops_remaining = standard_track.sound_players[player].next.loops_remaining
            standard_track.sound_players[player].current.sound_priority = standard_track.sound_players[player].next.sound_priority
            standard_track.sound_players[player].current.marker_count = standard_track.sound_players[player].next.marker_count

            for buffer_pos in range(standard_track.sound_players[player].current.marker_count):
                standard_track.sound_players[player].current.markers[buffer_pos] = standard_track.sound_players[player].next.markers[buffer_pos]

            if standard_track.sound_players[player].current.sound_has_ducking:
                standard_track.sound_players[player].current.sound_has_ducking = True
                standard_track.sound_players[player].current.ducking_settings.track_bit_mask = standard_track.sound_players[player].next.ducking_settings.track_bit_mask
                standard_track.sound_players[player].current.ducking_settings.attack_start_pos = standard_track.sound_players[player].next.ducking_settings.attack_start_pos
                standard_track.sound_players[player].current.ducking_settings.attack_duration = standard_track.sound_players[player].next.ducking_settings.attack_duration
                standard_track.sound_players[player].current.ducking_settings.attenuation_volume = standard_track.sound_players[player].next.ducking_settings.attenuation_volume
                standard_track.sound_players[player].current.ducking_settings.release_start_pos = standard_track.sound_players[player].next.ducking_settings.release_start_pos
                standard_track.sound_players[player].current.ducking_settings.release_duration = standard_track.sound_players[player].next.ducking_settings.release_duration
            else:
                standard_track.sound_players[player].current.sound_has_ducking = False

            # Update the current input sound buffer to point to the new sound
            sound_buffer = <Uint8*> standard_track.sound_players[player].current.chunk.abuf

        # Check if player has a sound pending playback (ready to start)
        if standard_track.sound_players[player].status is player_pending:
            # Sound ready to start playback, send event notification and set status to playing
            send_sound_started_notification(track.number, player,
                                            standard_track.sound_players[player].current.sound_id,
                                            standard_track.sound_players[player].current.sound_instance_id,
                                            callback_data.notification_messages,
                                            sdl_ticks)

            standard_track.sound_players[player].status = player_playing

        # Process markers (do any markers fall in the current processing window?)
        for marker_id in range(standard_track.sound_players[player].current.marker_count):
            if standard_track.sound_players[player].current.sample_pos <= standard_track.sound_players[player].current.markers[
                marker_id] < standard_track.sound_players[player].current.sample_pos + buffer_length:

                # Marker is in window, send notification
                send_sound_marker_notification(track.number, player,
                                               standard_track.sound_players[player].current.sound_id,
                                               standard_track.sound_players[player].current.sound_instance_id,
                                               callback_data.notification_messages,
                                               sdl_ticks,
                                               marker_id)

        # If audio playback object is playing, add it's samples to the output buffer (scaled by sample volume)
        if standard_track.sound_players[player].status is player_playing and \
                        standard_track.sound_players[player].current.volume > 0 and \
                        standard_track.sound_players[player].current.chunk != NULL:

            # Process sound ducking (if applicable)
            if standard_track.sound_players[player].current.sound_has_ducking:

                ducking_is_active = False
                control_point_pos = standard_track.sound_players[player].current.sample_pos

                # Loop over control points in sound
                for control_point in range(CONTROL_POINTS_PER_BUFFER):

                    # Determine control point ducking stage and calculate control point
                    if control_point_pos >= standard_track.sound_players[player].current.ducking_settings.release_start_pos + standard_track.sound_players[player].current.ducking_settings.release_duration:
                        # Ducking finished
                        standard_track.sound_players[player].current.ducking_control_points[control_point] = MIX_MAX_VOLUME

                    elif control_point_pos >= standard_track.sound_players[player].current.ducking_settings.release_start_pos:
                        # Ducking release stage
                        ducking_is_active = True
                        progress = (control_point_pos - standard_track.sound_players[player].current.ducking_settings.release_start_pos) / standard_track.sound_players[player].current.ducking_settings.release_duration
                        standard_track.sound_players[player].current.ducking_control_points[control_point] = \
                            lerpU8(in_out_quad(progress), standard_track.sound_players[player].current.ducking_settings.attenuation_volume, MIX_MAX_VOLUME)

                    elif control_point_pos >= standard_track.sound_players[player].current.ducking_settings.attack_start_pos + standard_track.sound_players[player].current.ducking_settings.attack_duration:
                        # Ducking hold state
                        ducking_is_active = True
                        standard_track.sound_players[player].current.ducking_control_points[control_point] = standard_track.sound_players[player].current.ducking_settings.attenuation_volume

                    elif control_point_pos >= standard_track.sound_players[player].current.ducking_settings.attack_start_pos:
                        # Ducking attack stage
                        ducking_is_active = True
                        progress = (control_point_pos - standard_track.sound_players[player].current.ducking_settings.attack_start_pos) / standard_track.sound_players[player].current.ducking_settings.attack_duration
                        standard_track.sound_players[player].current.ducking_control_points[control_point] = \
                            lerpU8(in_out_quad(progress), MIX_MAX_VOLUME, standard_track.sound_players[player].current.ducking_settings.attenuation_volume)

                    else:
                        # Ducking delay stage
                        standard_track.sound_players[player].current.ducking_control_points[control_point] = MIX_MAX_VOLUME

                    # Move to next control point
                    control_point_pos += samples_per_control_point

                    # Loop back to beginning of sound (if looping)
                    if control_point_pos >= standard_track.sound_players[player].current.chunk.alen and standard_track.sound_players[player].current.loops_remaining != 0:
                        control_point_pos -= standard_track.sound_players[player].current.chunk.alen

                # Apply ducking to target track(s) (when applicable)
                if ducking_is_active:
                    for track_num in range(callback_data.track_count):
                        if (1 << track_num) & standard_track.sound_players[player].current.ducking_settings.track_bit_mask:
                            if callback_data.tracks[track_num].ducking_is_active:
                                # Ducking is already active on the track; take the minimum value at each control point
                                for control_point in range(CONTROL_POINTS_PER_BUFFER):
                                    callback_data.tracks[track_num].ducking_control_points[control_point] = min(
                                        callback_data.tracks[track_num].ducking_control_points[control_point],
                                        standard_track.sound_players[player].current.ducking_control_points[control_point])
                            else:
                                # Ducking not active on track; set it to active and assign control points
                                callback_data.tracks[track_num].ducking_is_active = True
                                for control_point in range(CONTROL_POINTS_PER_BUFFER):
                                    callback_data.tracks[track_num].ducking_control_points[control_point] = standard_track.sound_players[player].current.ducking_control_points[control_point]

            # Loop over destination buffer, mixing in the source sample
            volume = standard_track.sound_players[player].current.volume
            while buffer_pos < buffer_length:

                # Calculate volume at the control rate (handle fading)
                if (buffer_pos % samples_per_control_point) == 0:
                    if standard_track.sound_players[player].current.fading_status == fading_status_fading_in:
                        volume = <Uint8> (in_out_quad(
                            (standard_track.sound_players[player].current.fade_in_steps - standard_track.sound_players[player].current.fade_steps_remaining) /
                            standard_track.sound_players[player].current.fade_in_steps) * standard_track.sound_players[
                                              player].current.volume)
                        standard_track.sound_players[player].current.fade_steps_remaining -= 1
                        if standard_track.sound_players[player].current.fade_steps_remaining == 0:
                            standard_track.sound_players[player].current.fading_status = fading_status_not_fading

                    # Note: fading out only happens while the sound is stopping and therefore is not
                    #       handled here

                    else:
                        volume = standard_track.sound_players[player].current.volume

                mix_sound_sample_to_buffer(sound_buffer,
                                           standard_track.sound_players[player].current.sample_pos,
                                           volume,
                                           output_buffer,
                                           buffer_pos)

                # Advance the source sample pointer to the next sample (2 bytes)
                standard_track.sound_players[player].current.sample_pos += BYTES_PER_SAMPLE

                # Advance the output buffer pointer to the next sample (2 bytes)
                buffer_pos += BYTES_PER_SAMPLE

                # Check if we are at the end of the source sample buffer (loop if applicable)
                if standard_track.sound_players[player].current.sample_pos >= standard_track.sound_players[player].current.chunk.alen:
                    end_of_sound_processing(cython.address(standard_track.sound_players[player]),
                                            callback_data.notification_messages, sdl_ticks)
                    if standard_track.sound_players[player].status is player_finished:
                        break

                # TODO: Hold sound processing until ducking has finished
                # It is possible to have the ducking release finish after the sound has stopped.  In that
                # case, silence should be generated until the ducking is done.

        # Check if the sound has finished
        if standard_track.sound_players[player].status is player_finished:
            send_sound_stopped_notification(track.number, player,
                                     standard_track.sound_players[player].current.sound_id,
                                     standard_track.sound_players[player].current.sound_instance_id,
                                     callback_data.notification_messages,
                                     sdl_ticks)
            standard_track.sound_players[player].status = player_idle

cdef inline void end_of_sound_processing(SoundPlayer* player,
                                         NotificationMessageContainer **notification_messages,
                                         Uint32 sdl_ticks) nogil:
    """
    Determines the action to take at the end of the sound (loop or stop) based on
    the current settings.  This function should be called when a sound processing
    loop has reached the end of the source buffer.
    Args:
        player: SoundPlayer pointer
        notification_messages: The NotificationMessageContainer object containing all notification messages
        sdl_ticks: The current SDL timestamp (in ticks)
    """
    # Check if we are at the end of the source sample buffer (loop if applicable)
    if player.current.loops_remaining > 0:
        # At the end and still loops remaining, loop back to the beginning
        player.current.loops_remaining -= 1
        player.current.sample_pos = 0
        player.current.current_loop += 1
        send_sound_looping_notification(player.track_num, player.player,
                                 player.current.sound_id, player.current.sound_instance_id,
                                 notification_messages, sdl_ticks)

    elif player.current.loops_remaining == 0:
        # At the end and not looping, the sample has finished playing
        player.status = player_finished

    else:
        # Looping infinitely, loop back to the beginning
        player.current.sample_pos = 0
        player.current.current_loop += 1
        send_sound_looping_notification(player.track_num, player.player,
                                 player.current.sound_id, player.current.sound_instance_id,
                                 notification_messages, sdl_ticks)

cdef inline void send_sound_started_notification(int track_num, int player,
                                                 long sound_id, long sound_instance_id,
                                                 NotificationMessageContainer **notification_messages,
                                                 Uint32 sdl_ticks) nogil:
    """
    Sends a sound started notification
    Args:
        track_num: The track number on which the event occurred
        player: The sound player number on which the event occurred
        sound_id: The sound id
        sound_instance_id: The sound instance id
        notification_messages: A pointer to the notification messages structures
        sdl_ticks: The current SDL tick time
    """
    cdef int message_index = get_available_notification_message(notification_messages)
    if message_index != -1:
        notification_messages[message_index].message = notification_sound_started
        notification_messages[message_index].track = track_num
        notification_messages[message_index].player = player
        notification_messages[message_index].sound_id = sound_id
        notification_messages[message_index].sound_instance_id = sound_instance_id
        notification_messages[message_index].time = sdl_ticks

cdef inline void send_sound_stopped_notification(int track_num, int player,
                                                 long sound_id, long sound_instance_id,
                                                 NotificationMessageContainer **notification_messages,
                                                 Uint32 sdl_ticks) nogil:
    """
    Sends a sound stopped notification
    Args:
        track_num: The track number on which the event occurred
        player: The sound player number on which the event occurred
        sound_id: The sound id
        sound_instance_id: The sound instance id
        notification_messages: A pointer to the notification messages structures
        sdl_ticks: The current SDL tick time
    """
    cdef int message_index = get_available_notification_message(notification_messages)
    if message_index != -1:
        notification_messages[message_index].message = notification_sound_stopped
        notification_messages[message_index].track = track_num
        notification_messages[message_index].player = player
        notification_messages[message_index].sound_id = sound_id
        notification_messages[message_index].sound_instance_id = sound_instance_id
        notification_messages[message_index].time = sdl_ticks

cdef inline void send_sound_looping_notification(int track_num, int player,
                                                 long sound_id, long sound_instance_id,
                                                 NotificationMessageContainer **notification_messages,
                                                 Uint32 sdl_ticks) nogil:
    """
    Sends a sound looping notification
    Args:
        track_num: The track number on which the event occurred
        player: The sound player number on which the event occurred
        sound_id: The sound id
        sound_instance_id: The sound instance id
        notification_messages: A pointer to the notification messages structures
        sdl_ticks: The current SDL tick time
    """
    cdef int message_index = get_available_notification_message(notification_messages)
    if message_index != -1:
        notification_messages[message_index].message = notification_sound_looping
        notification_messages[message_index].track = track_num
        notification_messages[message_index].player = player
        notification_messages[message_index].sound_id = sound_id
        notification_messages[message_index].sound_instance_id = sound_instance_id
        notification_messages[message_index].time = sdl_ticks

cdef inline void send_sound_marker_notification(int track_num, int player,
                                                long sound_id, long sound_instance_id,
                                                NotificationMessageContainer **notification_messages,
                                                Uint32 sdl_ticks,
                                                int marker_id) nogil:
    """
    Sends a sound marker notification message
    Args:
        track_num: The track number on which the event occurred
        player: The sound player number on which the event occurred
        sound_id: The sound id
        sound_instance_id: The sound instance id
        notification_messages: A pointer to the notification messages structures
        sdl_ticks: The current SDL tick time
        marker_id: The id of the marker being sent for the specified sound
    """
    cdef int message_index = get_available_notification_message(notification_messages)
    if message_index != -1:
        notification_messages[message_index].message = notification_sound_marker
        notification_messages[message_index].track = track_num
        notification_messages[message_index].player = player
        notification_messages[message_index].sound_id = sound_id
        notification_messages[message_index].sound_instance_id = sound_instance_id
        notification_messages[message_index].time = sdl_ticks
        notification_messages[message_index].data.marker.id = marker_id

cdef void apply_track_ducking(TrackState* track, Uint32 buffer_size, AudioCallbackData* callback_data) nogil:
    """
    Applies ducking to the specified track (if applicable).
    Args:
        track: A pointer to the TrackState struct for the track
        buffer_size: The size of the current output audio buffer (in bytes)
        callback_data: The AudioCallbackData struct
    """
    cdef Uint32 buffer_pos = 0
    cdef Uint32 samples_per_control_point = buffer_size // CONTROL_POINTS_PER_BUFFER
    cdef Uint8 ducking_volume
    cdef int control_point

    if track == NULL:
        return

    # Only need to process when ducking is active
    if track.ducking_is_active:
        # Loop over track buffer
        for control_point in range(CONTROL_POINTS_PER_BUFFER):
            ducking_volume = track.ducking_control_points[control_point]
            if ducking_volume < MIX_MAX_VOLUME:
                apply_volume_to_buffer_range(<Uint8*> track.buffer, buffer_pos, ducking_volume,
                                             samples_per_control_point)

            buffer_pos += samples_per_control_point

cdef inline void apply_volume_to_buffer_range(Uint8 *buffer, Uint32 start_pos, Uint8 volume, Uint32 length=2) nogil:
    """
    Applies the specified volume to a range of samples in an audio buffer at the specified
    buffer position.
    Args:
        buffer: The audio buffer
        start_pos: The starting audio buffer position at which to apply the volume level
        volume: The volume level to apply (8-bit unsigned value 0 to MIX_MAX_VOLUME)
        length: The number of bytes to apply the volume to
    """
    cdef Sample16Bit buffer_sample
    cdef Uint32 buffer_pos = start_pos

    while buffer_pos < start_pos + length:
        buffer_sample.bytes.byte0 = buffer[buffer_pos]
        buffer_sample.bytes.byte1 = buffer[buffer_pos + 1]
        buffer_sample.value = (buffer_sample.value * volume) // MIX_MAX_VOLUME
        buffer[buffer_pos] = buffer_sample.bytes.byte0
        buffer[buffer_pos + 1] = buffer_sample.bytes.byte1
        buffer_pos += BYTES_PER_SAMPLE

cdef void apply_volume_to_buffer(Uint8 *buffer, int buffer_length, Uint8 volume) nogil:
    """
    Applies the specified volume to an entire audio buffer.
    Args:
        buffer: The audio buffer
        buffer_length: The length of the audio buffer (in bytes)
        volume: The volume level to apply (8-bit unsigned value 0 to MIX_MAX_VOLUME)
    """
    cdef int temp_sample
    cdef Sample16Bit sample
    cdef int buffer_pos = 0

    while buffer_pos < buffer_length:

        # Get sound sample (2 bytes), combine into a 16-bit value and apply sound volume
        sample.bytes.byte0 = buffer[buffer_pos]
        sample.bytes.byte1 = buffer[buffer_pos + 1]
        temp_sample = (sample.value * volume) // MIX_MAX_VOLUME

        # Put the new sample back into the output buffer (from a 32-bit value
        # back to a 16-bit value that we know is in 16-bit value range)
        sample.value = temp_sample
        buffer[buffer_pos] = sample.bytes.byte0
        buffer[buffer_pos + 1] = sample.bytes.byte1

        buffer_pos += BYTES_PER_SAMPLE

cdef inline void mix_sound_sample_to_buffer(Uint8 *sound_buffer, Uint32 sample_pos, Uint8 sound_volume,
                                            Uint8 *output_buffer, Uint32 buffer_pos) nogil:
    """
    Mixes a single sample into a buffer at the specified volume
    Args:
        sound_buffer: The source sound buffer
        sample_pos: The source sound sample position (buffer index)
        sound_volume: The volume to apply to the source sound
        output_buffer: The output sound buffer
        buffer_pos: The output sound buffer position (buffer index)
    """
    cdef int temp_sample
    cdef Sample16Bit sound_sample
    cdef Sample16Bit output_sample

    # Get sound sample (2 bytes), combine into a 16-bit value and apply sound volume
    sound_sample.bytes.byte0 = sound_buffer[sample_pos]
    sound_sample.bytes.byte1 = sound_buffer[sample_pos + 1]

    # Get sample (2 bytes) already in the output buffer and combine into 16-bit value
    output_sample.bytes.byte0 = output_buffer[buffer_pos]
    output_sample.bytes.byte1 = output_buffer[buffer_pos + 1]

    # Apply volume to sound sample
    sound_sample.value = (sound_sample.value * sound_volume) // MIX_MAX_VOLUME

    # Calculate the new output sample (mix the existing output sample with
    # the new source sound).  The temp sample is a 32-bit value to avoid overflow.
    temp_sample = output_sample.value + sound_sample.value

    # Clip the temp sample back to a 16-bit value (will cause distortion if samples
    # on channel are too loud)
    if temp_sample > MAX_AUDIO_VALUE_S16:
        temp_sample = MAX_AUDIO_VALUE_S16
    elif temp_sample < MIN_AUDIO_VALUE_S16:
        temp_sample = MIN_AUDIO_VALUE_S16

    # Put the new mixed output sample back into the output buffer (from a 32-bit value
    # back to a 16-bit value that we know is in 16-bit value range)
    output_sample.value = temp_sample
    output_buffer[buffer_pos] = output_sample.bytes.byte0
    output_buffer[buffer_pos + 1] = output_sample.bytes.byte1

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

cdef void mix_track_to_output(Uint8 *track_buffer, Uint8 track_volume, Uint8 *output_buffer, Uint32 buffer_size) nogil:
    """
    Mixes a track buffer into the master audio output buffer.
    Args:
        track_buffer: A track's audio buffer
        track_volume: The track volume (0 to 128)
        output_buffer: The master audio output buffer.
        buffer_size: The audio buffer size to process.

    """

    cdef Sample16Bit track_sample
    cdef Sample16Bit output_sample

    cdef int temp_sample
    cdef Uint32 index

    index = 0
    while index < buffer_size:

        # Get sound sample (2 bytes), combine into a 16-bit value and apply sound volume
        track_sample.bytes.byte0 = track_buffer[index]
        track_sample.bytes.byte1 = track_buffer[index + 1]
        track_sample.value = track_sample.value * track_volume // MIX_MAX_VOLUME

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

        index += BYTES_PER_SAMPLE

cdef int get_available_notification_message(NotificationMessageContainer **notification_messages) nogil:
    """
    Returns the index of the first available notification message. If all notification messages
    are currently in use, -1 is returned.
    :param notification_messages: The pool of audio messages
    :return: The index of the first available notification message.  -1 if all are in use.
    """
    if notification_messages == NULL:
        return -1

    for i in range(MAX_NOTIFICATION_MESSAGES):
        if notification_messages[i].message == notification_not_in_use:
            return i

    return -1


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
    cdef AudioCallbackData *_audio_callback_data
    cdef SDL_mutex *mutex
    cdef object log

    # Track attributes need to be stored in a C struct in order for them to be accessible in
    # the SDL callback functions without the GIL (for performance reasons).  The TrackState
    # struct is allocated during construction and freed during destruction.
    cdef TrackState *state

    def __cinit__(self, *args, **kw):
        """C constructor"""
        self.state = NULL
        self._audio_callback_data = NULL
        self.mutex = NULL

    def __init__(self, dict sound_instances_by_id, object audio_callback_data, str name, int track_num, int buffer_size, float volume=1.0):
        """
        Constructor
        Args:
            sound_instances_by_id: A dictionary of all active sound instance objects keyed by id
            audio_callback_data: The AudioCallbackData pointer wrapped in a PyCapsule object
            name: The track name
            track_num: The track number (corresponds to the SDL_Mixer channel number)
            buffer_size: The length of the track audio buffer in bytes
            volume: The track volume (0.0 to 1.0)
        """
        self.log = logging.getLogger("Track")
        self._sound_instances_by_id = sound_instances_by_id
        self._name = name
        self._number = track_num

        # The easiest way to pass a C pointer in a constructor is to wrap it in a PyCapsule
        # (see https://docs.python.org/3.4/c-api/capsule.html).  This basically wraps the
        # pointer in a Python object. It can be extracted using PyCapsule_GetPointer.
        self._audio_callback_data = <AudioCallbackData*>pycapsule.PyCapsule_GetPointer(audio_callback_data, NULL)
        self.mutex = self._audio_callback_data.mutex

        # Allocate memory for the track state (common among all track types)
        self.state = <TrackState*> PyMem_Malloc(sizeof(TrackState))
        self.state.type = track_type_none
        self.state.type_state = NULL
        self.state.number = track_num
        self.state.buffer = <void *>PyMem_Malloc(buffer_size)
        self.state.buffer_size = buffer_size
        self.log.debug("Allocated track audio buffer (%d bytes)", buffer_size)
        self.volume = volume

    def __repr__(self):
        return '<Track.{}.{}>'.format(self.number, self.name)

    cdef TrackState *get_state(self):
        return self.state

    property name:
        def __get__(self):
            return self._name

    property volume:
        def __get__(self):
            return round(self.state.volume / MIX_MAX_VOLUME, 2)

        def __set__(self, float volume):
            if self.state != NULL:
                # Volume used in SDL_Mixer is an integer between 0 and MIX_MAX_VOLUME (0 to 128)
                SDL_LockMutex(self.mutex)
                self.state.volume = <Uint8>min(max(volume * MIX_MAX_VOLUME, 0), MIX_MAX_VOLUME)
                SDL_UnlockMutex(self.mutex)

    @property
    def number(self):
        """Return the track number"""
        cdef int number = -1
        if self.state != NULL:
            SDL_LockMutex(self.mutex)
            number = self.state.number
            SDL_UnlockMutex(self.mutex)
        return number

    @property
    def supports_in_memory_sounds(self):
        """Return whether or not track supports in-memory sounds"""
        raise NotImplementedError('Must be overridden in derived class')

    @property
    def supports_streaming_sounds(self):
        """Return whether or not track supports streaming sounds"""
        raise NotImplementedError('Must be overridden in derived class')

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

    def stop_all_sounds(self):
        """
        Stops all playing sounds immediately on the track.
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
    cdef object _sound_queue
    cdef dict _sound_queue_items
    cdef int _max_simultaneous_sounds
    cdef int _queue_entry_id

    # Track state needs to be stored in a C struct in order for them to be accessible in
    # the SDL callback functions without the GIL (for performance reasons).
    # The TrackStandardState struct is allocated during construction and freed during
    # destruction.
    cdef TrackStandardState *type_state

    def __init__(self, dict sound_instances_by_id, object audio_callback_data, str name, int track_num, int buffer_size,
                 int max_simultaneous_sounds=MAX_SIMULTANEOUS_SOUNDS_DEFAULT,
                 float volume=1.0):
        """
        Constructor
        Args:
            sound_instances_by_id: A dictionary of all active sound instance objects keyed by id
            audio_callback_data: The AudioCallbackData struct wrapped in a PyCapsule
            name: The track name
            track_num: The track number
            buffer_size: The length of the track audio buffer in bytes
            max_simultaneous_sounds: The maximum number of sounds that can be played simultaneously
                on the track
            volume: The track volume (0.0 to 1.0)
        """
        # IMPORTANT: Call super class init function to allocate track state memory!
        super().__init__(sound_instances_by_id, audio_callback_data, name, track_num, buffer_size, volume)

        self.log = logging.getLogger("Track." + str(track_num) + ".TrackStandard." + name)

        SDL_LockMutex(self.mutex)

        self._sound_queue = PriorityQueue()
        self._sound_queue_items = dict()
        self._queue_entry_id = 0

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
            self.type_state.sound_players[i].current.chunk = NULL
            self.type_state.sound_players[i].current.loops_remaining = 0
            self.type_state.sound_players[i].current.current_loop = 0
            self.type_state.sound_players[i].current.volume = 0
            self.type_state.sound_players[i].current.sample_pos = 0
            self.type_state.sound_players[i].current.sound_id = 0
            self.type_state.sound_players[i].current.sound_instance_id = 0
            self.type_state.sound_players[i].current.sound_priority = 0
            self.type_state.sound_players[i].current.sound_has_ducking = False
            self.type_state.sound_players[i].current.ducking_stage = ducking_stage_idle
            self.type_state.sound_players[i].next.chunk = NULL
            self.type_state.sound_players[i].next.loops_remaining = 0
            self.type_state.sound_players[i].next.current_loop = 0
            self.type_state.sound_players[i].next.volume = 0
            self.type_state.sound_players[i].next.sample_pos = 0
            self.type_state.sound_players[i].next.sound_id = 0
            self.type_state.sound_players[i].next.sound_instance_id = 0
            self.type_state.sound_players[i].next.sound_priority = 0
            self.type_state.sound_players[i].next.sound_has_ducking = False
            self.type_state.sound_players[i].next.ducking_stage = ducking_stage_idle

        SDL_UnlockMutex(self.mutex)

    def __dealloc__(self):
        """Destructor"""

        SDL_LockMutex(self.mutex)

        # Free the specific track type state and other allocated memory
        if self.state != NULL:
            PyMem_Free(self.type_state.sound_players)
            PyMem_Free(self.type_state)
            self.state = NULL

        SDL_UnlockMutex(self.mutex)

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
        # NOTE: The SDL Mutex must be held while calling this function

        for index in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[index].status == player_idle:
                SDL_UnlockMutex(self.mutex)
                return index

        return -1

    def process(self):
        """Processes the track queue each tick."""

        cdef bint keep_checking = True
        cdef int idle_sound_player

        # Lock the mutex to ensure no audio data is changed during the playback processing
        # (multi-threaded protection)
        SDL_LockMutex(self.mutex)

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

        # Unlock the mutex since we are done accessing the audio data
        SDL_UnlockMutex(self.mutex)

    cdef RequestMessageContainer* _get_available_request_message(self):
        """
        Returns a pointer to the first available request message.
        If all request messages are currently in use, NULL is returned.
        :return: The index of the first available audio event.  -1 if all
            are in use.
        """
        # NOTE: The SDL Mutex must be held while calling this function

        cdef RequestMessageContainer *request_message
        for i in range(MAX_REQUEST_MESSAGES):
            if self._audio_callback_data.request_messages[i].message == request_not_in_use:
                request_message = <RequestMessageContainer*> self._audio_callback_data.request_messages[i]
                SDL_UnlockMutex(self.mutex)
                return request_message

        return NULL

    def process_notification_message(self, int message_num):
        """Process a notification message to this track"""
        cdef NotificationMessageContainer *notification_message = self._audio_callback_data.notification_messages[message_num]

        if notification_message == NULL:
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

        # Event has been processed, reset it so it may be used again
        notification_message.message = notification_not_in_use
        notification_message.sound_id = 0
        notification_message.sound_instance_id = 0

    def _get_next_sound(self):
        """
        Returns the next sound in the priority queue ready for playback.

        Returns: A SoundInstance object. If the queue is empty, None is returned.

        This method ensures that the sound that is returned has not expired.
        If the next sound in the queue has expired, it is discarded and the
        next sound that has not expired is returned.
        """
        # We don't want to go through the entire sound queue more than once
        # in this method so keep track of the number of items we are
        # retrieving from the queue and exit when we have gone through
        # all items once.
        cdef list queue_entry_ids_retrieved = list()
        while True:

            # Each item in the queue is a list containing the following items:
            #    0 (priority): The priority of the returned sound
            #    1 (exp_time): The time (in ticks) after which the sound expires and should not be played
            #    2 (entry_id): The unique identifier for this queue entry (used to ensure queue can always
            #                  be properly sorted
            #    3 (sound): The Sound object ready for playback

            try:
                # Get the next item in the queue (sorted by priority and expiration time)
                queue_entry = self._sound_queue.get_nowait()

                # Check if we've already processed the entry during this call
                if queue_entry[2] in queue_entry_ids_retrieved:
                    # Already processed, put it back in the queue and return None
                    self._sound_queue.put(queue_entry)
                    return None

                # Keep track of entries we've processed during this call
                queue_entry_ids_retrieved.append(queue_entry[2])

                # Check if entry has already been marked as removed (sound is None)
                if queue_entry[3] is None:
                    continue

            except Empty:
                # Queue is empty
                return None

            # If the sound is still loading and not expired, put it back in the queue
            sound_instance = queue_entry[3]
            exp_time = queue_entry[1]
            if not sound_instance.sound.loaded and sound_instance.sound.loading and \
                    (exp_time is None or exp_time > time.time()):
                self._sound_queue.put(queue_entry)
                self.log.debug("Next pending sound in queue is still loading, "
                               "re-queueing sound %s",
                               queue_entry)
            else:
                # Remove the queue entry from the list of sounds in the queue
                if sound_instance in self._sound_queue_items:
                    del self._sound_queue_items[sound_instance]

                # Return the next sound from the priority queue if it has not expired
                if exp_time is None or exp_time > time.time():
                    self.log.debug("Retrieving next pending sound from queue %s", queue_entry)
                    sound_instance.set_pending()  # Notify sound instance it is no longer queued
                    return sound_instance
                else:
                    self.log.debug("Discarding expired sound from queue %s", queue_entry)
                    sound_instance.set_expired()  # Notify sound instance it has expired

        return None

    def _remove_sound_from_queue(self, sound_instance not None):
        """
        Removes a sound from the priority sound queue.
        Args:
            sound_instance: The sound object to remove
        """

        # The sounds will not actually be removed from the priority queue because that
        # could corrupt the queue heap structure, but are simply set to None so they
        # will not be played.  After marking queue entry as None, the dictionary keeping
        # track of sounds in the queue is updated.
        if sound_instance in self._sound_queue_items:
            entry = self._sound_queue_items[sound_instance]
            entry[3] = None
            self.log.debug("Removing pending sound from queue %s", sound_instance)
            sound_instance.set_canceled()
            del self._sound_queue_items[sound_instance]

    def _remove_all_sounds_from_queue(self):
        """Removes all sounds from the priority sound queue.
        """

        # The sounds will not actually be removed from the priority queue because that
        # could corrupt the queue heap structure, but are simply set to None so they
        # will not be played.  After marking queue entry as None, the dictionary keeping
        # track of sounds in the queue is updated.
        for sound_instance in self._sound_queue_items:
            entry = self._sound_queue_items[sound_instance]
            entry[3] = None
            self.log.debug("Removing pending sound from queue %s", sound_instance)
            sound_instance.set_canceled()

        self._sound_queue_items.clear()

    def play_sound(self, sound_instance not None):
        """
        Plays a sound on the current track.
        Args:
            sound_instance: The SoundInstance object to play
        """
        self.log.debug("play_sound - Processing sound '%s' for playback.", sound_instance.name)

        SDL_LockMutex(self.mutex)

        if sound_instance.max_queue_time is None:
            exp_time = None
        else:
            exp_time = time.time() + sound_instance.max_queue_time

        # Make sure sound is loaded.  If not, we assume the sound is being loaded and we
        # add it to the queue so it will be picked up on the next loop.
        if not sound_instance.sound.loaded:
            # If the sound is not already loading, load it now
            if not sound_instance.sound.loading:
                sound_instance.sound.load()

            if sound_instance.max_queue_time != 0:
                self._queue_sound(sound_instance=sound_instance, exp_time=exp_time)
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
                    self._queue_sound(sound_instance=sound_instance, exp_time=exp_time)

        SDL_UnlockMutex(self.mutex)

    def replace_sound(self, old_instance not None, sound_instance not None):
        """
        Replace a currently playing instance with another sound instance.
        Args:
            old_instance: The currently playing sound instance to replace
            sound_instance: The new sound instance to begin playing immediately
        """

        self.log.debug("replace_sound - Preparing to replace existing sound with a new sound instance")

        # Find which player is currently playing the specified sound instance to replace
        SDL_LockMutex(self.mutex)
        player = self._get_player_playing_sound_instance(old_instance)

        if player >= 0:
            self._play_sound_on_sound_player(sound_instance, player, force=True)
        else:
            self.log.debug("replace_sound - Could not locate specified sound instance to replace")
            sound_instance.set_canceled()

        SDL_UnlockMutex(self.mutex)

    def _queue_sound(self, sound_instance, exp_time=None):
        """Adds a sound to the queue to be played when a sound player becomes available.

        Args:
            sound_instance: The SoundInstance object to play.
            exp_time: Real world time of when this sound will expire.  It will not play
                if the queue is freed up after it expires.  None indicates the sound
                never expires and will eventually be played.

        Note that this method will insert this sound into a position in the
        queue based on its priority, so highest-priority sounds are played
        first.
        """

        # Note the negative operator in front of priority since this queue
        # retrieves the lowest values first, and MPF uses higher values for
        # higher priorities.
        entry = [-sound_instance.priority, exp_time, self._queue_entry_id, sound_instance]
        self._sound_queue.put(entry)
        self._queue_entry_id += 1

        # Notify sound instance it has been queued
        sound_instance.set_queued()

        # Save the new entry in a dictionary of entries keyed by sound.  This
        # dictionary is used to remove pending sounds from the priority queue.
        self._sound_queue_items[sound_instance] = entry

        self.log.debug("Queueing sound %s", entry)

    def stop_sound(self, sound_instance not None):
        """
        Stops all instances of the specified sound immediately on the track. Any queued instances
        will be removed from the queue.
        Args:
            sound_instance: The SoundInstance to stop
        """

        SDL_LockMutex(self.mutex)

        self.log.debug("Stopping sound %s and removing any pending instances from queue", sound_instance.name)

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and self.type_state.sound_players[
                i].current.sound_instance_id == sound_instance.id:
                # Set stop sound event
                request_message = self._get_available_request_message()
                if request_message != NULL:
                    request_message.message = request_sound_stop
                    request_message.sound_id = self.type_state.sound_players[i].current.sound_id
                    request_message.sound_instance_id = self.type_state.sound_players[i].current.sound_instance_id
                    request_message.track = self.number
                    request_message.player = i
                    request_message.time = SDL_GetTicks()

                    # Fade out
                    seconds_to_bytes_factor = self._audio_callback_data.sample_rate * self._audio_callback_data.audio_channels * BYTES_PER_SAMPLE
                    request_message.data.stop.fade_out_duration = sound_instance.fade_out * seconds_to_bytes_factor

                    # Adjust ducking (if necessary)
                    if sound_instance.ducking is not None:
                        request_message.data.stop.ducking_release_duration = min(
                            sound_instance.ducking.release * seconds_to_bytes_factor,
                            request_message.data.stop.fade_out_duration)
                else:
                    self.log.error(
                        "All internal audio messages are currently "
                        "in use, could not stop sound %s", sound_instance.name)

        # Remove any instances of the specified sound that are pending in the sound queue.
        self._remove_sound_from_queue(sound_instance)

        SDL_UnlockMutex(self.mutex)

    def stop_sound_looping(self, sound_instance not None):
        """
        Stops all instances of the specified sound on the track after they finish the current loop.
        Any queued instances of the sound will be removed.
        Args:
            sound_instance: The Sound to stop
        """

        SDL_LockMutex(self.mutex)

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and self.type_state.sound_players[
                i].current.sound_instance_id == sound_instance.id:
                # Set sound's loops_remaining variable to zero
                self.type_state.sound_players[i].current.loops_remaining = 0

        # Remove any instances of the specified sound that are pending in the sound queue.
        self._remove_sound_from_queue(sound_instance)

        SDL_UnlockMutex(self.mutex)

    def stop_all_sounds(self, float fade_out_seconds = 0.0):
        """
        Stops all playing sounds immediately on the track.
        Args:
            fade_out_seconds: The number of seconds to fade out the sounds before stopping
        """
        SDL_LockMutex(self.mutex)

        self.log.debug("Stopping all sounds and removing any pending sounds from queue")

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle:
                # Set stop sound event
                request_message = self._get_available_request_message()
                if request_message != NULL:
                    request_message.message = request_sound_stop
                    request_message.sound_id = self.type_state.sound_players[i].current.sound_id
                    request_message.sound_instance_id = self.type_state.sound_players[i].current.sound_instance_id
                    request_message.track = self.number
                    request_message.player = i
                    request_message.time = SDL_GetTicks()

                    # Fade out
                    seconds_to_bytes_factor = self._audio_callback_data.sample_rate * self._audio_callback_data.audio_channels * BYTES_PER_SAMPLE
                    request_message.data.stop.fade_out_duration = fade_out_seconds * seconds_to_bytes_factor

                    # Adjust ducking (if necessary)
                    # TODO: trigger ducking here
                    pass
                else:
                    self.log.error("All internal audio messages are currently in use, could not stop all sounds")

        # Remove all sounds that are pending in the sound queue.
        self._remove_all_sounds_from_queue()

        SDL_UnlockMutex(self.mutex)

    cdef tuple _get_sound_player_with_lowest_priority(self):
        """
        Retrieves the sound player currently with the lowest priority.

        Returns:
            A tuple consisting of the sound player index and the priority of
            the sound playing on that player (or None if the player is idle).

        """
        # NOTE: The SDL Mutex must be held while calling this function

        cdef int lowest_priority = 2147483647
        cdef int sound_player = -1
        cdef int i

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status == player_idle:
                SDL_UnlockMutex(self.mutex)
                return i, None
            elif self.type_state.sound_players[i].current.sound_priority < lowest_priority:
                lowest_priority = self.type_state.sound_players[i].current.sound_priority
                sound_player = i

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
        # NOTE: The SDL Mutex must be held while calling this function
        self.log.debug("_play_sound_on_sound_player: %s, %s, %s", str(sound_instance), str(player), str(force))

        # Get the sound sample buffer container
        cdef MixChunkContainer chunk_container = sound_instance.container
        cdef RequestMessageContainer *request_message

        if not sound_instance.sound.loaded:
            self.log.debug("Specified sound is not loaded, could not "
                           "play sound %s", sound_instance.name)
            return False

        # Make sure the player in range
        if player in range(self.type_state.sound_player_count):

            # If the specified sound player is not idle do not play the sound if force is not set
            if self.type_state.sound_players[player].status != player_idle and not force:
                self.log.debug("All sound players are currently in use, "
                               "could not play sound %s", sound_instance.name)
                return False

            # Set play sound event
            request_message = self._get_available_request_message()
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
                request_message.track = self.number
                request_message.player = player
                request_message.time = SDL_GetTicks()
                request_message.data.play.loops = sound_instance.loops
                request_message.data.play.priority = sound_instance.priority
                request_message.data.play.chunk = chunk_container.chunk

                # Conversion factor (seconds to bytes/buffer position)
                seconds_to_bytes_factor = self._audio_callback_data.sample_rate * self._audio_callback_data.audio_channels * BYTES_PER_SAMPLE

                request_message.data.play.start_at_position = <Uint32>(sound_instance.start_at * seconds_to_bytes_factor)
                request_message.data.play.fade_in_duration = <Uint32>(sound_instance.fade_in * seconds_to_bytes_factor)
                request_message.data.play.fade_out_duration = <Uint32>(sound_instance.fade_out * seconds_to_bytes_factor)

                # Volume must be converted from a float (0.0 to 1.0) to an 8-bit integer (0..MIX_MAX_VOLUME)
                request_message.data.play.volume = <Uint8>(sound_instance.volume * MIX_MAX_VOLUME)

                # If the sound has any markers, set them
                request_message.data.play.marker_count = sound_instance.marker_count
                if sound_instance.marker_count > 0:
                    for index in range(sound_instance.marker_count):
                        request_message.data.play.markers[index] = <long>(sound_instance.markers[index]['time'] * seconds_to_bytes_factor)

                # If the sound has ducking settings, apply them
                if sound_instance.ducking is not None and sound_instance.ducking.track_bit_mask != 0:
                    # To convert between the number of seconds and a buffer position (bytes), we need to
                    # account for the sample rate (sampes per second), the number of audio channels, and the
                    # number of bytes per sample (all samples are 16 bits)
                    seconds_to_bytes_factor = self._audio_callback_data.sample_rate * self._audio_callback_data.audio_channels * BYTES_PER_SAMPLE
    
                    request_message.data.play.sound_has_ducking = True
                    request_message.data.play.ducking_settings.track_bit_mask = sound_instance.ducking.track_bit_mask
                    request_message.data.play.ducking_settings.attack_start_pos = sound_instance.ducking.delay * seconds_to_bytes_factor
                    request_message.data.play.ducking_settings.attack_duration = sound_instance.ducking.attack * seconds_to_bytes_factor
                    request_message.data.play.ducking_settings.attenuation_volume = <Uint8>(sound_instance.ducking.attenuation * MIX_MAX_VOLUME)
                    request_message.data.play.ducking_settings.release_start_pos = sound_instance.ducking.release_point * seconds_to_bytes_factor
                    request_message.data.play.ducking_settings.release_duration = sound_instance.ducking.release * seconds_to_bytes_factor
                else:
                    request_message.data.play.sound_has_ducking = False
    

            else:
                self.log.warning("All internal audio messages are "
                               "currently in use, could not play sound %s"
                               , sound_instance.name)
                return False

            self.log.debug("Sound %s is set to begin playback on player %d (loops=%d)",
                           sound_instance.name, player, sound_instance.loops)

            return True

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
        # NOTE: The SDL Mutex must be held while calling this function

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and \
                            self.type_state.sound_players[i].current.sound_instance_id == sound_instance.id:
                return i

        return -1

    def get_status(self):
        """
        Get the current track status (status of all sound players on the track).
        Used for debugging and testing.
        Returns:
            A list of status dictionaries containing the current settings for each
            sound player.
        """
        SDL_LockMutex(self.mutex)
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

        SDL_UnlockMutex(self.mutex)

        return status

    def get_sound_queue_count(self):
        """
        Gets the number of sounds currently in the track sound queue.
        Returns:
            Integer number of sounds currently in the track sound queue.
        """
        return self._sound_queue.qsize()

    def get_sound_players_in_use_count(self):
        """
        Gets the current count of sound players in use on the track.  Used for
        debugging and testing.
        Returns:
            Integer number of sound players currently in use on the track.
        """
        players_in_use_count = 0
        SDL_LockMutex(self.mutex)
        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle:
                players_in_use_count += 1
        SDL_UnlockMutex(self.mutex)
        return players_in_use_count

    def sound_is_playing(self, sound not None):
        """Returns whether or not the specified sound is currently playing on the track"""
        SDL_LockMutex(self.mutex)
        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and \
                            self.type_state.sound_players[i].current.sound_id == sound.id:
                SDL_UnlockMutex(self.mutex)
                return True

        SDL_UnlockMutex(self.mutex)
        return False

    def sound_instance_is_playing(self, sound_instance not None):
        """Returns whether or not the specified sound instance is currently playing on the track"""
        SDL_LockMutex(self.mutex)
        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and \
                            self.type_state.sound_players[i].current.sound_instance_id == sound_instance.id:
                SDL_UnlockMutex(self.mutex)
                return True

        SDL_UnlockMutex(self.mutex)
        return False

    def sound_is_in_queue(self, sound not None):
        """Returns whether or not an instance of the specified sound is currently in the queue"""
        for sound_instance in self._sound_queue_items:
            if sound_instance.sound.id == sound.id:
                return True

        return False

    def sound_instance_is_in_queue(self, sound_instance not None):
        """Returns whether or not the specified sound instance is currently in the queue"""
        return sound_instance in self._sound_queue_items

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

        SDL_LockMutex(self.mutex)

        # Set track type specific settings
        self.state.type = track_type_live_loop

        # Allocate memory for the specific track type state struct (TrackLiveLoopState)
        self.type_state = <TrackLiveLoopState*> PyMem_Malloc(sizeof(TrackLiveLoopState))
        self.state.type_state = <void*>self.type_state

        self.type_state.master_sound_player = <SoundPlayer*> PyMem_Malloc(sizeof(SoundPlayer))
        self.type_state.slave_sound_player_count = 0
        self.type_state.slave_sound_players = NULL

        # TODO: Allocate slave sound players

    def __dealloc__(self):
        """Destructor"""

        SDL_LockMutex(self.mutex)

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

        SDL_UnlockMutex(self.mutex)

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

        SDL_LockMutex(self.mutex)

        # TODO: play the sound instance

        SDL_UnlockMutex(self.mutex)

    def stop_sound(self, sound_instance not None):
        """
        Stops all instances of the specified sound immediately on the track. Any queued instances
        will be removed from the queue.
        Args:
            sound_instance: The SoundInstance to stop
        """

        SDL_LockMutex(self.mutex)

        # TODO: stop the sound instance

        SDL_UnlockMutex(self.mutex)

    def stop_sound_looping(self, sound_instance not None):
        """
        Stops all instances of the specified sound on the track after they finish the current loop.
        Any queued instances of the sound will be removed.
        Args:
            sound_instance: The Sound to stop
        """

        SDL_LockMutex(self.mutex)

        # TODO: stop looping the sound instance

        SDL_UnlockMutex(self.mutex)

    def stop_all_sounds(self):
        """
        Stops all playing sounds immediately on the track.
        """
        SDL_LockMutex(self.mutex)

        # TODO: stop looping the sound instance

        SDL_UnlockMutex(self.mutex)

    def process(self):
        """Processes the track queue each tick."""
        pass


# ---------------------------------------------------------------------------
#    MixChunkContainer class
# ---------------------------------------------------------------------------
cdef class MixChunkContainer:
    """
    MixChunkContainer is a wrapper class to manage a SDL_Mixer Mix_Chunk C pointer (points
    to a block of memory that contains an audio sample in a format ready for playback).
    This class will properly unload/free the memory allocated when loading the sound when
    it is destroyed.
    """
    cdef Mix_Chunk *chunk

    def __init__(self):
        self.chunk = NULL

    def __dealloc__(self):
        if self.chunk != NULL:
            Mix_FreeChunk(self.chunk)
            self.chunk = NULL

    @property
    def loaded(self):
        """Returns whether or not the chunk is loaded in memory"""
        return self.chunk != NULL

    @property
    def length(self):
        """Returns the length of the Mix_Chunk (in samples)"""
        if self.chunk == NULL:
            return 0
        else:
            return self.chunk.alen
