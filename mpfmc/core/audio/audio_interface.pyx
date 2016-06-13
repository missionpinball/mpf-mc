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

__version_info__ = ('0', '30', '0-dev16')
__version__ = '.'.join(__version_info__)

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
DEF MAX_TRACK_DUCKING_ENVELOPES = 32
DEF MAX_AUDIO_MESSAGES = 64
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
    cdef int mixer_channel
    cdef list tracks
    cdef object mc
    cdef object log

    # In order to get the SDL_Mixer library to work with the desired features needed for the
    # media controller, a sound must be played at all times on a mixer channel.  A sound
    # containing silence is created and stored in the audio interface to be played by the
    # SDL_Mixer channel.
    cdef Mix_Chunk *raw_chunk_silence

    cdef AudioCallbackData *audio_callback_data

    def __cinit__(self, *args, **kw):
        self.sample_rate = 0
        self.audio_channels = 0
        self.buffer_samples = 0
        self.buffer_size = 0
        self.supported_formats = 0
        self.mixer_channel = -1
        self.raw_chunk_silence = NULL
        self.audio_callback_data = NULL

    def __init__(self, mc, rate=44100, channels=2, buffer_samples=4096):
        """
        Initializes the AudioInterface.
        Args:
            rate: The audio sample rate used in the library
            channels: The number of channels to use (1=mono, 2=stereo)
            buffer_samples: The audio buffer size to use (in number of samples, must be power of two)
        """
        self.mc = mc
        self.log = logging.getLogger("AudioInterface")

        # Initialize threading in the extension library and acquire the Python global interpreter lock
        PyEval_InitThreads()

        # Make sure buffer samples is a power of two (required by SDL2)
        if not AudioInterface.power_of_two(buffer_samples):
            self.log.error('Buffer samples is required to be a power of two')
            raise AudioException("Unable to initialize Audio Interface: "
                                 "Buffer samples is required to be a power of two")

        # Initialize the SDL audio system
        if SDL_Init(SDL_INIT_AUDIO) < 0:
            self.log.error('SDL_Init error - %s' % SDL_GetError())
            raise AudioException('Unable to initialize SDL (SDL_Init call failed: %s)' % SDL_GetError())

        # Initialize the SDL_Mixer library to establish the output audio format and encoding
        # (sample rate, bit depth, buffer size)
        if Mix_OpenAudio(rate, AUDIO_S16SYS, channels, buffer_samples):
            self.log.error('Mix_OpenAudio error - %s' % SDL_GetError())
            raise AudioException('Unable to open audio for output (Mix_OpenAudio failed: %s)' % SDL_GetError())

        self.log.info("Initialized {}".format(AudioInterface.get_version()))
        self.log.debug("Loaded {}".format(AudioInterface.get_sdl_version()))
        self.log.debug("Loaded {}".format(AudioInterface.get_sdl_mixer_version()))

        # Lock SDL from calling the audio callback functions
        SDL_LockAudio()

        # Determine the actual audio format in use by the opened audio device.  This may or may not match
        # the parameters used to initialize the audio interface.
        self.buffer_samples = buffer_samples
        self.log.debug('Settings requested - rate: {}, channels: {}, buffer: {} samples'
                       .format(rate, channels, buffer_samples))
        Mix_QuerySpec(&self.sample_rate, NULL, &self.audio_channels)
        self.log.debug('Settings in use - rate: {}, channels: {}, buffer: {} samples'.format(
            self.sample_rate, self.audio_channels, self.buffer_samples))

        # Set the size of the track audio buffers (samples * channels * size of 16-bit int) for 16-bit audio
        self.buffer_size = self.buffer_samples * self.audio_channels * sizeof(Uint16)

        # Allocate memory for the audio callback data structure
        self.audio_callback_data = <AudioCallbackData*> PyMem_Malloc(sizeof(AudioCallbackData))

        # Initialize the audio callback data structure
        self.audio_callback_data.sample_rate = self.sample_rate
        self.audio_callback_data.audio_channels = self.audio_channels
        self.audio_callback_data.master_volume = MIX_MAX_VOLUME // 2
        self.audio_callback_data.track_count = 0
        self.audio_callback_data.tracks = <TrackAttributes**> PyMem_Malloc(MAX_TRACKS * sizeof(TrackAttributes*))
        self.audio_callback_data.messages = <AudioMessageContainer**> PyMem_Malloc(
            MAX_AUDIO_MESSAGES * sizeof(AudioMessageContainer*))

        # Initialize audio messages
        for i in range(MAX_AUDIO_MESSAGES):
            self.audio_callback_data.messages[i] = <AudioMessageContainer*> PyMem_Malloc(sizeof(AudioMessageContainer))
            self.audio_callback_data.messages[i].message = message_not_in_use
            self.audio_callback_data.messages[i].sound_id = 0
            self.audio_callback_data.messages[i].track = 0
            self.audio_callback_data.messages[i].player = 0
            self.audio_callback_data.messages[i].time = 0

        self.audio_callback_data.mutex = SDL_CreateMutex()

        # Initialize the supported SDL_Mixer library formats
        self.supported_formats = Mix_Init(MIX_INIT_OGG)

        self._initialize_silence()
        self._initialize_audio_callback()

        # Unlock the SDL audio callback functions
        SDL_UnlockAudio()

        self.tracks = []

    def __del__(self):

        self.log.debug("Shutting down and cleaning up allocated memory...")

        # Stop audio processing (will stop all SDL callbacks)
        self.disable()

        # Remove tracks
        self.tracks.clear()

        # Free all allocated memory
        for i in range(MAX_AUDIO_MESSAGES):
            PyMem_Free(self.audio_callback_data.messages[i])

        PyMem_Free(self.audio_callback_data.messages)
        PyMem_Free(self.audio_callback_data.tracks)
        SDL_DestroyMutex(self.audio_callback_data.mutex)
        PyMem_Free(self.audio_callback_data)

        # SDL_Mixer and SDL no longer needed
        Mix_Quit()
        SDL_Quit()

    def _initialize_silence(self):
        """
        Initializes and generates an audio chunk/sample containing silence (used to play on each
        track since each track in SDL_Mixer must play something to call its effects callback
        functions which are used in this library to perform the actual sound generation/mixing)
        """
        # Create the audio buffer containing silence
        cdef Uint8 *silence = NULL
        cdef Uint32 length = self.buffer_size
        silence = <Uint8 *> calloc(1, length)

        # Instruct SDL_Mixer to load the silence into a chunk
        self.raw_chunk_silence = Mix_QuickLoad_RAW(silence, length)
        if self.raw_chunk_silence == NULL:
            raise AudioException('Unable to load generated silence sample required for playback')
        else:
            self.log.debug("Silence audio chunk initialized (required for SDL_Mixer callback)")


    def _initialize_audio_callback(self):
        # Set the number of channels to mix (will cause existing channels to be stopped and restarted if playing)
        # This is an SDL_Mixer library function call.
        channels = Mix_AllocateChannels(1)
        self.log.debug("SDL_Mixer - Allocated {} channel for final audio output".format(channels))
        self.mixer_channel = 0

        # Ensure channel volume is at maximum (should be the default, but we'll set it manually
        # in case the default ever changes)
        Mix_Volume(self.mixer_channel, MIX_MAX_VOLUME)

        # Setup callback function for mixer channel depending upon the audio format used
        cdef Mix_EffectFunc_t audio_callback_fn = AudioInterface.audio_callback

        # Register the audio callback function that will perform the actual mixing of sounds.
        # A pointer to the audio callback data is passed to the callback function that contains
        # all necessary data to perform the playback and mixing of sounds.
        # This is an SDL_Mixer library function call.
        Mix_RegisterEffect(self.mixer_channel, audio_callback_fn, NULL, <void *> self.audio_callback_data)

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

    def convert_seconds_to_samples(self, int seconds):
        """Converts the specified number of seconds into samples (based on current sample rate)"""
        return self.sample_rate * seconds

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
        cdef float master_volume
        SDL_LockMutex(self.audio_callback_data.mutex)
        master_volume = self.audio_callback_data.master_volume / MIX_MAX_VOLUME
        SDL_UnlockMutex(self.audio_callback_data.mutex)
        return master_volume

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
        cdef int channel
        SDL_LockAudio()
        channel = Mix_Playing(self.mixer_channel) == 1
        SDL_UnlockAudio()
        return channel

    def enable(self, int fade_sec=0):
        """
        Enables audio playback with a fade in (begins audio processing)
        Args:
            fade_sec:  The number of seconds over which to fade in the audio
        """
        cdef int fade_ms = 0

        self.log.debug("Enabling audio playback")

        SDL_LockAudio()
        if fade_sec > 0:
            fade_ms = fade_sec // 1000
            Mix_FadeInChannel(self.mixer_channel, self.raw_chunk_silence, -1, fade_ms)
        else:
            Mix_PlayChannel(self.mixer_channel, self.raw_chunk_silence, -1)

        SDL_UnlockAudio()

    def disable(self, int fade_sec=0):
        """
        Disables audio playback after fading out (stops audio processing)
        Args:
            fade_sec:  The number of seconds over which to fade out the audio
        """
        cdef int fade_ms = 0

        self.log.debug("Disabling audio playback")

        SDL_LockAudio()
        if fade_sec > 0:
            fade_ms = fade_sec // 1000
            Mix_FadeOutChannel(self.mixer_channel, fade_ms)
        else:
            Mix_HaltChannel(self.mixer_channel)

        SDL_UnlockAudio()

    @classmethod
    def get_max_tracks(cls):
        """ Returns the maximum number of tracks allowed. """
        return MAX_TRACKS

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

    def create_track(self, str name not None,
                     int max_simultaneous_sounds=MAX_SIMULTANEOUS_SOUNDS_DEFAULT,
                     float volume=1.0):
        """
        Creates a new track in the audio interface
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
                           "({}) has been reached.".format(MAX_TRACKS))
            return None

        # Make sure track name does not already exist (no duplicates allowed)
        name = name.lower()
        for track in self.tracks:
            if name == track.name:
                self.log.error("Add track failed - the track name '{}' already exists."
                               .format(name))
                return None

        # Make sure audio callback function cannot be called while we are changing the track data
        SDL_LockAudio()

        # Create the new track
        new_track = Track(pycapsule.PyCapsule_New(self.audio_callback_data, NULL, NULL),
                          name,
                          track_num,
                          self.buffer_size,
                          max_simultaneous_sounds,
                          volume)
        self.tracks.append(new_track)

        # Update audio callback data with new track
        self.audio_callback_data.track_count = len(self.tracks)
        self.audio_callback_data.tracks[track_num] = new_track.attributes

        # Allow audio callback function to be called again
        SDL_UnlockAudio()

        self.log.debug("The '{}' track has successfully been created.".format(name))

        return new_track

    @staticmethod
    def load_sound(str file_name):
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
        cdef char*c_file_name = py_byte_file_name

        # Attempt to load the file
        cdef Mix_Chunk *chunk = Mix_LoadWAV(c_file_name)
        if chunk == NULL:
            log = logging.getLogger('AudioInterface')
            log.error("Unable to load sound from source file '{}' - {}"
                      .format(file_name, SDL_GetError()))
            return None

        # Create a Python container object to wrap the Mix_Chunk C pointer
        cdef MixChunkContainer mc = MixChunkContainer()
        mc.chunk = chunk
        return mc

    @staticmethod
    def unload_sound(container):
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

    def stop_sound(self, sound not None):
        """
        Stops all instances of the specified sound immediately on all tracks.
        Args:
            sound: The Sound to stop
        """
        for track in self.tracks:
            track.stop_sound(sound)

    def process(self):
        """Process tick function for the audio interface."""

        # Process tracks
        for track in self.tracks:
            track.process()

        # Process any internal notification messages that may cause other messages to be generated
        SDL_LockMutex(self.audio_callback_data.mutex)
        for i in range(MAX_AUDIO_MESSAGES):
            if self.audio_callback_data.messages[i].message == message_sound_started:
                sound = self.mc.sounds_by_id[self.audio_callback_data.messages[i].sound_id]
                if sound.events_when_played is not None:
                    for event in sound.events_when_played:
                        self.mc.bcp_processor.send('trigger', name=event)

                # Event has been processed, reset it so it may be used again
                self.audio_callback_data.messages[i].message = message_not_in_use

            elif self.audio_callback_data.messages[i].message == message_sound_stopped:
                sound = self.mc.sounds_by_id[self.audio_callback_data.messages[i].sound_id]
                if sound.events_when_stopped is not None:
                    for event in sound.events_when_stopped:
                        self.mc.bcp_processor.send('trigger', name=event)

                # Event has been processed, reset it so it may be used again
                self.audio_callback_data.messages[i].message = message_not_in_use

            elif self.audio_callback_data.messages[i].message == message_sound_marker:
                # TODO: Process sound marker event

                # Event has been processed, reset it so it may be used again
                self.audio_callback_data.messages[i].message = message_not_in_use

        SDL_UnlockMutex(self.audio_callback_data.mutex)

    def get_in_use_sound_event_count(self):
        """
        Returns the number of sound messages currently in use.  Used for debugging and testing.
        """
        in_use_event_count = 0
        SDL_LockMutex(self.audio_callback_data.mutex)
        for i in range(MAX_AUDIO_MESSAGES):
            if self.audio_callback_data.messages[i].message != message_not_in_use:
                in_use_event_count += 1

        SDL_UnlockMutex(self.audio_callback_data.mutex)
        return in_use_event_count

    @staticmethod
    cdef void audio_callback(int channel, void *output_buffer, int length, void *data) nogil:
        """
        Main audio callback function (called from SDL_Mixer).
        Args:
            channel: The SDL_Mixer channel number (corresponds to the audio interface channel number)
            output_buffer: The SDL_Mixer audio buffer for the mixer channel to process
            length: The length (bytes) of the audio buffer
            data: A pointer to the AudioCallbackData class for the channel (contains all audio
                processing-related settings and state, ex: interface settings, tracks, sound
                players, ducking envelopes, etc.)

        Notes:
            This static function is responsible for filling the supplied audio buffer with sound.
            samples. The function is called during an audio channel effect callback.  This audio
            library only uses a single SDL_Mixer channel for all output.  Individual track buffers
            are maintained in each Track object and are processed during this callback.
        """
        cdef Uint32 buffer_length

        if data == NULL:
            return

        buffer_length = <Uint32>length

        # SDL_Mixer channel should already be playing 'silence', a silent sample generated in memory.
        # This is so SDL_Mixer thinks the channel is active and will call the channel callback
        # function which is used to read and mix the actual source audio.
        cdef AudioCallbackData *callback_data = <AudioCallbackData*> data

        # Lock the mutex to ensure no audio data is changed during the playback processing
        # (multi-threaded protection)
        SDL_LockMutex(callback_data.mutex)

        # Process any internal sound messages that may affect sound playback (play and stop messages)
        process_sound_messages(callback_data)

        # Loop over tracks, mixing the playing sounds into the track's audio buffer
        for track_num in range(callback_data.track_count):
            # Zero out track buffer (start with silence)
            memset(callback_data.tracks[track_num].buffer, 0, buffer_length)

            # Mix any playing sounds into the track buffer
            mix_sounds_to_track(callback_data.tracks[track_num],
                                buffer_length,
                                callback_data)

        # Loop over tracks again, mixing down tracks to the master output buffer
        for track_num in range(callback_data.track_count):

            # Apply ducking envelopes to track audio buffer
            apply_track_ducking_envelopes(callback_data.tracks[track_num], buffer_length,
                                          callback_data.audio_channels, callback_data)

            # Apply track volume and mix to output buffer
            mix_track_to_output(<Uint8*> callback_data.tracks[track_num].buffer,
                                callback_data.tracks[track_num].volume,
                                <Uint8*> output_buffer,
                                buffer_length)

        # Apply master volume to output buffer
        apply_volume_to_buffer(<Uint8*> output_buffer, buffer_length, callback_data.master_volume)

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

cdef void process_sound_messages(AudioCallbackData *callback_data) nogil:
    """
    Processes any new sound messages that should be processed prior to the main
    audio callback processing (such as sound play and sound stop messages).
    Args:
        callback_data: The audio callback data structure
    """
    cdef int i
    cdef int track
    cdef int player

    # Loop over messages
    for i in range(MAX_AUDIO_MESSAGES):

        if callback_data.messages[i].message == message_sound_play:
            # Update player to start playing new sound
            track = callback_data.messages[i].track
            player = callback_data.messages[i].player
            callback_data.tracks[track].sound_players[player].status = player_pending
            callback_data.tracks[track].sound_players[player].current.sample_pos = 0
            callback_data.tracks[track].sound_players[player].current.current_loop = 0
            callback_data.tracks[track].sound_players[player].current.sound_id = callback_data.messages[i].sound_id
            callback_data.tracks[track].sound_players[player].current.chunk = callback_data.messages[i].data.play.chunk
            callback_data.tracks[track].sound_players[player].current.volume = callback_data.messages[i].data.play.volume
            callback_data.tracks[track].sound_players[player].current.loops_remaining = callback_data.messages[i].data.play.loops
            callback_data.tracks[track].sound_players[player].current.sound_priority = callback_data.messages[i].data.play.priority

            # Clear event since it has been processed
            callback_data.messages[i].message = message_not_in_use

        elif callback_data.messages[i].message == message_sound_stop:
            # Update player to stop playing sound
            track = callback_data.messages[i].track
            player = callback_data.messages[i].player
            callback_data.tracks[track].sound_players[player].status = player_stopping

            # Clear event since it has been processed
            callback_data.messages[i].message = message_not_in_use

        elif callback_data.messages[i].message == message_sound_replace:
            # Update player to stop playing current sound and start playing new sound
            track = callback_data.messages[i].track
            player = callback_data.messages[i].player
            callback_data.tracks[track].sound_players[player].status = player_replacing
            callback_data.tracks[track].sound_players[player].next.sample_pos = 0
            callback_data.tracks[track].sound_players[player].next.current_loop = 0
            callback_data.tracks[track].sound_players[player].next.sound_id = callback_data.messages[i].sound_id
            callback_data.tracks[track].sound_players[player].next.chunk = callback_data.messages[i].data.play.chunk
            callback_data.tracks[track].sound_players[player].next.volume = callback_data.messages[i].data.play.volume
            callback_data.tracks[track].sound_players[player].next.loops_remaining = callback_data.messages[i].data.play.loops
            callback_data.tracks[track].sound_players[player].next.sound_priority = callback_data.messages[i].data.play.priority

            # Clear event since it has been processed
            callback_data.messages[i].message = message_not_in_use

cdef void mix_sounds_to_track(TrackAttributes *track, Uint32 buffer_size, AudioCallbackData *callback_data) nogil:
    """
    Mixes any sounds that are playing on the specified track into the specified audio buffer.
    Args:
        track: A pointer to the TrackAttributes data structure for the track
        buffer_size: The length of the destination audio buffer (bytes)
        callback_data: The audio callback data structure
    Notes:
        Audio messages are generated.
    """
    if track == NULL:
        return

    # Get the current clock from SDL (it is used for the audio timing master)
    cdef Uint32 sdl_ticks = SDL_GetTicks()

    # Setup source (sound) and destination (track) buffer pointers/values
    cdef Uint8 *sound_buffer
    cdef Uint8 *output_buffer = <Uint8*> track.buffer

    cdef int event_index
    cdef Uint32 index
    cdef Uint32 fade_out_duration
    cdef Uint32 sound_samples_remaining
    cdef Uint8 volume
    cdef DuckingSettings *ducking_settings
    cdef TrackAttributes *target_track
    cdef DuckingEnvelope *envelope

    # Loop over track sound players
    for player in range(track.max_simultaneous_sounds):

        # If the player is idle, there is nothing to do so move on to the next player
        if track.sound_players[player].status is player_idle:
            continue

        index = 0

        # Check if player has been requested to stop a sound
        if track.sound_players[player].status is player_stopping:
            # Get source sound buffer (read one byte at a time, bytes will be combined into a
            # 16-bit sample value before being mixed)
            sound_buffer = <Uint8*> track.sound_players[player].current.chunk.abuf

            sound_samples_remaining = track.sound_players[player].current.chunk.alen - track.sound_players[
                player].current.sample_pos
            fade_out_duration = min(buffer_size,
                                    <Uint32>(callback_data.sample_rate * callback_data.audio_channels *
                                          QUICK_FADE_DURATION_SECS),
                                    sound_samples_remaining)
            volume = track.sound_players[player].current.volume

            if track.sound_players[player].current.sound_has_ducking:
                # Initiate a fast ducking release (10 ms)
                ducking_settings = cython.address(track.sound_players[player].current.ducking_settings)
                target_track = callback_data.tracks[ducking_settings.track]
                envelope = target_track.ducking_envelopes[ducking_settings.envelope_num]
                envelope.stage = envelope_stage_release
                envelope.stage_duration = <Sint32>(callback_data.sample_rate * callback_data.audio_channels *
                                                QUICK_FADE_DURATION_SECS)
                envelope.stage_initial_volume = envelope.current_volume
                envelope.stage_target_volume = MIX_MAX_VOLUME
                envelope.stage_pos = 0

            # Loop over destination buffer, mixing in the source sample
            while index < fade_out_duration:
                mix_sound_sample_to_buffer(sound_buffer,
                                           track.sound_players[player].current.sample_pos,
                                           volume,
                                           output_buffer,
                                           index)

                # Advance the source sample pointer to the next sample (2 bytes)
                track.sound_players[player].current.sample_pos += BYTES_PER_SAMPLE

                # Advance the output buffer pointer to the next sample (2 bytes)
                index += BYTES_PER_SAMPLE

                # Check if we are at the end of the source sample buffer
                if track.sound_players[player].current.sample_pos >= track.sound_players[player].current.chunk.alen:
                    end_of_sound_processing(cython.address(track.sound_players[player]))
                    if track.sound_players[player].status is player_finished:
                        break

                # Set volume for next loop
                volume = <Uint8> (
                    (1.0 - in_out_quad(index / fade_out_duration)) * track.sound_players[player].current.volume)

            # Update sound player status to finished
            track.sound_players[player].status = player_finished

        # Check if player has been requested to stop a sound and immediately replace it with another sound
        if track.sound_players[player].status is player_replacing:
            # Get source sound buffer (read one byte at a time, bytes will be combined into a
            # 16-bit sample value before being mixed)
            sound_buffer = <Uint8*> track.sound_players[player].current.chunk.abuf

            sound_samples_remaining = track.sound_players[player].current.chunk.alen - track.sound_players[
                player].current.sample_pos
            fade_out_duration = min(buffer_size,
                                    <Uint32>(callback_data.sample_rate * callback_data.audio_channels *
                                          QUICK_FADE_DURATION_SECS),
                                    sound_samples_remaining)
            volume = track.sound_players[player].current.volume

            if track.sound_players[player].current.sound_has_ducking:
                # Initiate a fast ducking release (10 ms)
                ducking_settings = cython.address(track.sound_players[player].current.ducking_settings)
                target_track = callback_data.tracks[ducking_settings.track]
                envelope = target_track.ducking_envelopes[ducking_settings.envelope_num]
                envelope.stage = envelope_stage_release
                envelope.stage_duration = <Sint32>callback_data.sample_rate * callback_data.audio_channels // 100
                envelope.stage_initial_volume = envelope.current_volume
                envelope.stage_target_volume = MIX_MAX_VOLUME
                envelope.stage_pos = 0

            # Loop over destination buffer, mixing in the source sample
            while index < fade_out_duration:
                mix_sound_sample_to_buffer(sound_buffer,
                                           track.sound_players[player].current.sample_pos,
                                           volume,
                                           output_buffer,
                                           index)

                # Advance the source sample pointer to the next sample (2 bytes)
                track.sound_players[player].current.sample_pos += BYTES_PER_SAMPLE

                # Advance the output buffer pointer to the next sample (2 bytes)
                index += BYTES_PER_SAMPLE

                # Check if we are at the end of the source sample buffer (loop if applicable)
                if track.sound_players[player].current.sample_pos >= track.sound_players[player].current.chunk.alen:
                    end_of_sound_processing(cython.address(track.sound_players[player]))
                    if track.sound_players[player].status is player_finished:
                        break

                # Set volume for next loop
                volume = <int> (
                    (1.0 - in_out_quad(index / fade_out_duration)) * track.sound_players[player].current.volume)

            # Send audio event that the sound has stopped
            send_sound_stopped_event(track.number, player,
                                     track.sound_players[player].current.sound_id,
                                     callback_data.messages,
                                     sdl_ticks)

            # Update sound player status to finished
            track.sound_players[player].status = player_pending

            # Copy sound player settings from next sound to current
            callback_data.tracks[track.number].sound_players[player].status = player_pending
            callback_data.tracks[track.number].sound_players[player].current.sample_pos = \
                callback_data.tracks[track.number].sound_players[player].next.sample_pos
            callback_data.tracks[track.number].sound_players[player].current.current_loop = \
                callback_data.tracks[track.number].sound_players[player].next.current_loop
            callback_data.tracks[track.number].sound_players[player].current.sound_id = \
                callback_data.tracks[track.number].sound_players[player].next.sound_id
            callback_data.tracks[track.number].sound_players[player].current.chunk = \
                callback_data.tracks[track.number].sound_players[player].next.chunk
            callback_data.tracks[track.number].sound_players[player].current.volume = \
                callback_data.tracks[track.number].sound_players[player].next.volume
            callback_data.tracks[track.number].sound_players[player].current.loops_remaining = \
                callback_data.tracks[track.number].sound_players[player].next.loops_remaining
            callback_data.tracks[track.number].sound_players[player].current.sound_priority = \
                callback_data.tracks[track.number].sound_players[player].next.sound_priority

        # Check if player has a sound pending playback (ready to start)
        if track.sound_players[player].status is player_pending:
            # Sound ready to start playback, send event notification and set status to playing
            event_index = get_available_audio_message(callback_data.messages)
            if event_index != -1:
                callback_data.messages[event_index].message = message_sound_started
                callback_data.messages[event_index].track = track.number
                callback_data.messages[event_index].player = player
                callback_data.messages[event_index].sound_id = \
                    track.sound_players[player].current.sound_id
                callback_data.messages[event_index].time = sdl_ticks

            track.sound_players[player].status = player_playing

        # If audio playback object is playing, add it's samples to the output buffer (scaled by sample volume)
        if track.sound_players[player].status is player_playing and \
                        track.sound_players[player].current.volume > 0 and \
                        track.sound_players[player].current.chunk != NULL:

            # Get source sound buffer (read one byte at a time, bytes will be combined into a
            # 16-bit sample value before being mixed)
            sound_buffer = <Uint8*> track.sound_players[player].current.chunk.abuf

            if track.sound_players[player].current.sound_has_ducking:
                ducking_settings = cython.address(track.sound_players[player].current.ducking_settings)
                if track.sound_players[player].current.current_loop == 0 and <Sint32>track.sound_players[
                    player].current.sample_pos <= ducking_settings.attack_start_pos < <Sint32>(track.sound_players[
                    player].current.sample_pos + buffer_size):

                    # Ducking attack starts in this callback frame, set ducking envelope settings
                    target_track = callback_data.tracks[ducking_settings.track]
                    envelope = target_track.ducking_envelopes[ducking_settings.envelope_num]
                    envelope.stage = envelope_stage_attack
                    envelope.stage_duration = ducking_settings.attack_duration
                    envelope.stage_initial_volume = envelope.current_volume
                    envelope.stage_target_volume = ducking_settings.attenuation_volume
                    envelope.stage_pos = <Sint32>track.sound_players[
                                             player].current.sample_pos - ducking_settings.attack_start_pos

                if track.sound_players[player].current.loops_remaining == 0 and <Sint32>track.sound_players[
                    player].current.sample_pos <= ducking_settings.release_start_pos < <Sint32>(track.sound_players[
                    player].current.sample_pos + buffer_size):

                    # Ducking release starts in this callback frame, set ducking envelope settings
                    target_track = callback_data.tracks[ducking_settings.track]
                    envelope = target_track.ducking_envelopes[ducking_settings.envelope_num]
                    envelope.stage = envelope_stage_release
                    envelope.stage_duration = ducking_settings.release_duration
                    envelope.stage_initial_volume = envelope.current_volume
                    envelope.stage_target_volume = MIX_MAX_VOLUME
                    envelope.stage_pos = <Sint32>track.sound_players[
                                             player].current.sample_pos - ducking_settings.release_start_pos

            # Loop over destination buffer, mixing in the source sample
            while index < buffer_size:

                mix_sound_sample_to_buffer(sound_buffer,
                                           track.sound_players[player].current.sample_pos,
                                           track.sound_players[player].current.volume,
                                           output_buffer,
                                           index)

                # Advance the source sample pointer to the next sample (2 bytes)
                track.sound_players[player].current.sample_pos += BYTES_PER_SAMPLE

                # Advance the output buffer pointer to the next sample (2 bytes)
                index += BYTES_PER_SAMPLE

                # Check if we are at the end of the source sample buffer (loop if applicable)
                if track.sound_players[player].current.sample_pos >= track.sound_players[player].current.chunk.alen:
                    end_of_sound_processing(cython.address(track.sound_players[player]))
                    if track.sound_players[player].status is player_finished:
                        break

        # Check if the sound has finished
        if track.sound_players[player].status is player_finished:
            send_sound_stopped_event(track.number, player,
                                     track.sound_players[player].current.sound_id,
                                     callback_data.messages,
                                     sdl_ticks)
            track.sound_players[player].status = player_idle

cdef inline void end_of_sound_processing(SoundPlayer* player) nogil:
    """
    Determines the action to take at the end of the sound (loop or stop) based on
    the current settings.  This function should be called when a sound processing
    loop has reached the end of the source buffer.
    Args:
        player: SoundPlayer pointer
    """
    # Check if we are at the end of the source sample buffer (loop if applicable)
    if player.current.loops_remaining > 0:
        # At the end and still loops remaining, loop back to the beginning
        player.current.loops_remaining -= 1
        player.current.sample_pos = 0
        player.current.current_loop += 1
    elif player.current.loops_remaining == 0:
        # At the end and not looping, the sample has finished playing
        player.status = player_finished
    else:
        # Looping infinitely, loop back to the beginning
        player.current.sample_pos = 0
        player.current.current_loop += 1

cdef inline void send_sound_stopped_event(int track_num, int player, long sound_id,
                                          AudioMessageContainer **messages, Uint32 sdl_ticks) nogil:
    """
    Sends a sound stopped audio event
    Args:
        track_num: The track number on which the event occurred
        player: The sound player number on which the event occurred
        sound_id: The sound id
        messages: A pointer to the audio messages structures
        sdl_ticks: The current SDL tick time
    """
    event_index = get_available_audio_message(messages)
    if event_index != -1:
        messages[event_index].message = message_sound_stopped
        messages[event_index].track = track_num
        messages[event_index].player = player
        messages[event_index].sound_id = sound_id
        messages[event_index].time = sdl_ticks

cdef void apply_volume_to_buffer(Uint8 *buffer, int buffer_length, Uint8 volume) nogil:
    """
    Applies the specified volume to an entire audio buffer.
    Args:
        buffer: The audio buffer
        buffer_length: The length of the audio buffer
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

        # Clip the temp sample back to a 16-bit value (will cause distortion if samples
        # on channel are too loud)
        if temp_sample > MAX_AUDIO_VALUE_S16:
            temp_sample = MAX_AUDIO_VALUE_S16
        elif temp_sample < MIN_AUDIO_VALUE_S16:
            temp_sample = MIN_AUDIO_VALUE_S16

        # Put the new sample back into the output buffer (from a 32-bit value
        # back to a 16-bit value that we know is in 16-bit value range)
        sample.value = temp_sample
        buffer[buffer_pos] = sample.bytes.byte0
        buffer[buffer_pos + 1] = sample.bytes.byte1

        buffer_pos += BYTES_PER_SAMPLE

cdef inline void apply_volume_to_buffer_sample(Uint8 *buffer, Uint32 buffer_pos, Uint8 volume, Uint32 sample_count=1) nogil:
    """
    Applies the specified volume to one or more samples in an audio buffer
    at the specified buffer position.
    Args:
        buffer: The audio buffer
        buffer_pos: The audio buffer position at which to apply the volume level
        volume: The volume level to apply (8-bit unsigned value 0 to MIX_MAX_VOLUME)
        sample_count: The number of samples to apply the volume level to
    """
    cdef Sample16Bit buffer_sample
    cdef Uint32 sample = 0

    while sample < sample_count:
        buffer_sample.bytes.byte0 = buffer[buffer_pos + BYTES_PER_SAMPLE * sample]
        buffer_sample.bytes.byte1 = buffer[buffer_pos + BYTES_PER_SAMPLE * sample + 1]
        buffer_sample.value = (buffer_sample.value * volume) // MIX_MAX_VOLUME
        buffer[buffer_pos + BYTES_PER_SAMPLE * sample] = buffer_sample.bytes.byte0
        buffer[buffer_pos + BYTES_PER_SAMPLE * sample + 1] = buffer_sample.bytes.byte1
        sample += 1

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

cdef void apply_track_ducking_envelopes(TrackAttributes* track, Uint32 buffer_size, int audio_channels,
                                        AudioCallbackData* callback_data) nogil:
    """
    Processes all active ducking envelopes for the specified track.
    Args:
        track: A pointer to the TrackAttributes struct for the track
        buffer_size: The size of the current output audio buffer
        audio_channels: The number of audio channels

    Notes:
        If multiple ducking envelopes are active simultaneously on the track, the minimum
        volume level across all active ducking envelopes for each sample is used.
    """
    if track == NULL:
        return

    cdef Uint8 ducking_volume
    cdef Uint8 volume
    cdef int envelope_num
    cdef Uint32 buffer_pos = 0
    cdef int buffer_step_size = BYTES_PER_SAMPLE * audio_channels

    # Loop over track buffers, one sample at a time
    while buffer_pos < buffer_size:
        ducking_volume = MIX_MAX_VOLUME
        for envelope_num in range(MAX_TRACK_DUCKING_ENVELOPES):
            volume = MIX_MAX_VOLUME
            if track.ducking_envelopes[envelope_num].stage == envelope_stage_idle:
                continue

            elif track.ducking_envelopes[envelope_num].stage == envelope_stage_sustain:
                volume = track.ducking_envelopes[envelope_num].stage_initial_volume
                track.ducking_envelopes[envelope_num].current_volume = volume

            elif track.ducking_envelopes[envelope_num].stage == envelope_stage_attack:
                if track.ducking_envelopes[envelope_num].stage_pos < 0:
                    volume = track.ducking_envelopes[envelope_num].stage_initial_volume
                else:
                    volume = lerpU8(in_out_quad(
                        track.ducking_envelopes[envelope_num].stage_pos / track.ducking_envelopes[
                            envelope_num].stage_duration), track.ducking_envelopes[envelope_num].stage_initial_volume,
                                    track.ducking_envelopes[envelope_num].stage_target_volume)

                track.ducking_envelopes[envelope_num].current_volume = volume
                track.ducking_envelopes[envelope_num].stage_pos += buffer_step_size

                # Check if attack stage has completed
                if track.ducking_envelopes[envelope_num].stage_pos >= track.ducking_envelopes[
                    envelope_num].stage_duration:
                    track.ducking_envelopes[envelope_num].stage = envelope_stage_sustain
                    track.ducking_envelopes[envelope_num].stage_initial_volume = track.ducking_envelopes[
                        envelope_num].stage_target_volume

            elif track.ducking_envelopes[envelope_num].stage == envelope_stage_release:
                if track.ducking_envelopes[envelope_num].stage_pos < 0:
                    volume = track.ducking_envelopes[envelope_num].stage_initial_volume
                else:
                    volume = lerpU8(in_out_quad(
                        track.ducking_envelopes[envelope_num].stage_pos / track.ducking_envelopes[
                            envelope_num].stage_duration), track.ducking_envelopes[envelope_num].stage_initial_volume,
                                    track.ducking_envelopes[envelope_num].stage_target_volume)

                track.ducking_envelopes[envelope_num].current_volume = volume
                track.ducking_envelopes[envelope_num].stage_pos += buffer_step_size

                if track.ducking_envelopes[envelope_num].stage_pos >= track.ducking_envelopes[
                    envelope_num].stage_duration:
                    track.ducking_envelopes[envelope_num].stage = envelope_stage_idle
                    track.ducking_envelopes[envelope_num].current_volume = MIX_MAX_VOLUME

            # Use the minimum volume level of all track ducking envelopes
            if volume < ducking_volume:
                ducking_volume = volume

        if ducking_volume < MIX_MAX_VOLUME:
            apply_volume_to_buffer_sample(<Uint8*> track.buffer, buffer_pos, ducking_volume,
                                          buffer_step_size // BYTES_PER_SAMPLE)

        buffer_pos += buffer_step_size

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

cdef int get_available_audio_message(AudioMessageContainer ** messages) nogil:
    """
    Returns the index of the first available audio message on the supplied track.
    If all audio messages are currently in use, -1 is returned.
    :param messages: The pool of audio messages
    :return: The index of the first available audio message.  -1 if all are in use.
    """
    if messages == NULL:
        return -1

    for i in range(MAX_AUDIO_MESSAGES):
        if messages[i].message == message_not_in_use:
            return i

    return -1


# ---------------------------------------------------------------------------
#    Track class
# ---------------------------------------------------------------------------
cdef class Track:
    """
    Track class
    """
    # The name of the track
    cdef str _name
    cdef object _sound_queue
    cdef dict _sound_queue_items
    cdef float _volume
    cdef AudioCallbackData *_audio_callback_data
    cdef SDL_mutex *mutex
    cdef object log

    # Track attributes need to be stored in a C struct in order for them to be accessible in
    # the SDL callback functions without the GIL (for performance reasons).  The TrackAttributes
    # struct is allocated during construction and freed during destruction.
    cdef TrackAttributes *attributes

    def __init__(self, object audio_callback_data, str name, int track_num, int buffer_size,
                 int max_simultaneous_sounds=MAX_SIMULTANEOUS_SOUNDS_DEFAULT,
                 float volume=1.0):
        """
        Constructor
        Args:
            name: The track name
            track_num: The track number (corresponds to the SDL_Mixer channel number)
            mutex: An SDL_mutex pointer wrapped in a PyCapsule.
            buffer_size: The length of the track audio buffer in bytes
            max_simultaneous_sounds: The maximum number of sounds that can be played simultaneously
                on the track
            volume: The track volume (0.0 to 1.0)
        """
        # The easiest way to pass a C pointer in a constructor is to wrap it in a PyCapsule
        # (see https://docs.python.org/3.4/c-api/capsule.html).  This basically wraps the
        # pointer in a Python object. It can be extracted using PyCapsule_GetPointer.
        self.log = logging.getLogger('AudioInterface.Track.' + str(track_num) + '.' + name)
        self._audio_callback_data = <AudioCallbackData*>pycapsule.PyCapsule_GetPointer(audio_callback_data, NULL)
        self.mutex = self._audio_callback_data.mutex

        SDL_LockMutex(self.mutex)

        self._sound_queue = PriorityQueue()
        self._sound_queue_items = {}

        # Make sure the number of simultaneous sounds is within the allowable range
        if max_simultaneous_sounds > MAX_SIMULTANEOUS_SOUNDS_LIMIT:
            self.log.warning("The maximum number of simultaneous sounds per track is {}"
                             .format(MAX_SIMULTANEOUS_SOUNDS_LIMIT))
            max_simultaneous_sounds = MAX_SIMULTANEOUS_SOUNDS_LIMIT
        elif max_simultaneous_sounds < 1:
            self.log.warning("The minimum number of simultaneous sounds per track is 1")
            max_simultaneous_sounds = 1

        # Allocate memory for the track attributes
        self.attributes = <TrackAttributes*> PyMem_Malloc(sizeof(TrackAttributes))
        self.attributes.number = track_num
        self.attributes.max_simultaneous_sounds = max_simultaneous_sounds
        self.attributes.buffer = PyMem_Malloc(buffer_size)
        self.attributes.buffer_size = buffer_size
        self.log.debug("Allocated track audio buffer ({} bytes)".format(buffer_size))
        self.volume = volume
        self._name = name

        # Allocate memory for the sound player structs needed for the desired number of
        # simultaneous sounds that can be played on the track.
        self.attributes.sound_players = <SoundPlayer*> PyMem_Malloc(self.max_simultaneous_sounds * sizeof(SoundPlayer))

        # Initialize sound player attributes
        for i in range(self.max_simultaneous_sounds):
            self.attributes.sound_players[i].status = player_idle
            self.attributes.sound_players[i].current.chunk = NULL
            self.attributes.sound_players[i].current.loops_remaining = 0
            self.attributes.sound_players[i].current.current_loop = 0
            self.attributes.sound_players[i].current.volume = 0
            self.attributes.sound_players[i].current.sample_pos = 0
            self.attributes.sound_players[i].current.sound_id = 0
            self.attributes.sound_players[i].current.sound_priority = 0
            self.attributes.sound_players[i].current.sound_has_ducking = 0
            self.attributes.sound_players[i].next.chunk = NULL
            self.attributes.sound_players[i].next.loops_remaining = 0
            self.attributes.sound_players[i].next.current_loop = 0
            self.attributes.sound_players[i].next.volume = 0
            self.attributes.sound_players[i].next.sample_pos = 0
            self.attributes.sound_players[i].next.sound_id = 0
            self.attributes.sound_players[i].next.sound_priority = 0
            self.attributes.sound_players[i].next.sound_has_ducking = 0

        self.attributes.ducking_envelopes = <DuckingEnvelope**> PyMem_Malloc(
            MAX_TRACK_DUCKING_ENVELOPES * sizeof(DuckingEnvelope*))

        # Initialize ducking envelope attributes
        for i in range(MAX_TRACK_DUCKING_ENVELOPES):
            self.attributes.ducking_envelopes[i] = <DuckingEnvelope*> PyMem_Malloc(sizeof(DuckingEnvelope))
            self.attributes.ducking_envelopes[i].stage = envelope_stage_idle
            self.attributes.ducking_envelopes[i].stage_pos = 0
            self.attributes.ducking_envelopes[i].stage_duration = 0
            self.attributes.ducking_envelopes[i].stage_initial_volume = MIX_MAX_VOLUME
            self.attributes.ducking_envelopes[i].stage_target_volume = MIX_MAX_VOLUME
            self.attributes.ducking_envelopes[i].current_volume = MIX_MAX_VOLUME

        SDL_UnlockMutex(self.mutex)

    def __dealloc__(self):

        SDL_LockMutex(self.mutex)

        # Free the attributes and other allocated memory
        if self.attributes != NULL:
            PyMem_Free(self.attributes.buffer)
            PyMem_Free(self.attributes.sound_players)

            for i in range(MAX_TRACK_DUCKING_ENVELOPES):
                PyMem_Free(self.attributes.ducking_envelopes[i])

            PyMem_Free(self.attributes.ducking_envelopes)
            PyMem_Free(self.attributes)
            self.attributes = NULL

        SDL_UnlockMutex(self.mutex)

    def __repr__(self):
        return '<Track.{}.{}>'.format(self.number, self.name)

    property name:
        def __get__(self):
            return self._name

    property volume:
        def __get__(self):
            return self._volume

        def __set__(self, float value):
            if self.attributes != NULL:
                value = min(max(value, 0.0), 1.0)
                self._volume = value

                SDL_LockMutex(self.mutex)

                # Volume used in SDL_Mixer is an integer between 0 and MIX_MAX_VOLUME (0 to 128)
                self.attributes.volume = int(self._volume * MIX_MAX_VOLUME)

                SDL_UnlockMutex(self.mutex)

    @property
    def number(self):
        cdef int number = -1
        if self.attributes != NULL:
            SDL_LockMutex(self.mutex)
            number = self.attributes.number
            SDL_UnlockMutex(self.mutex)
        return number

    @property
    def max_simultaneous_sounds(self):
        cdef int max_simultaneous_sounds = 0
        if self.attributes != NULL:
            SDL_LockMutex(self.mutex)
            max_simultaneous_sounds = self.attributes.max_simultaneous_sounds
            SDL_UnlockMutex(self.mutex)
        return max_simultaneous_sounds

    cdef int _get_idle_sound_player(self):
        """
        Returns the index of the first idle sound player on the track.  If all
        players are currently busy playing, -1 is returned.
        """
        SDL_LockMutex(self.mutex)
        for index in range(self.max_simultaneous_sounds):
            if self.attributes.sound_players[index].status == player_idle:
                SDL_UnlockMutex(self.mutex)
                return index

        SDL_UnlockMutex(self.mutex)
        return -1

    def process(self):
        """Processes the track queue each tick."""

        # Lock the mutex to ensure no audio data is changed during the playback processing
        # (multi-threaded protection)
        SDL_LockMutex(self.mutex)

        # See if there are now any idle sound players
        cdef int idle_sound_player = self._get_idle_sound_player()
        if idle_sound_player >= 0:
            # Found an idle player, check if there are any sounds queued for playback
            # Sound is returned as a tuple (sound, priority, settings)
            next_sound = self._get_next_sound()

            if next_sound is not None:
                self.log.debug("Getting sound from queue {}".format(next_sound))
                self._play_sound_on_sound_player(sound=next_sound[0],
                                                 player=idle_sound_player,
                                                 loops=next_sound[2]['loops'],
                                                 volume=next_sound[2]['volume'],
                                                 priority=next_sound[1])

        # Unlock the mutex since we are done accessing the audio data
        SDL_UnlockMutex(self.mutex)

    def _get_next_sound(self):
        """
        Returns the next sound in the priority queue ready for playback.

        Returns: A tuple of the Sound object, the priority, and dictionary of
            additional settings for playing the sound.  If the queue is empty,
            None is returned.

        This method ensures that the sound that is returned has not expired.
        If the next sound in the queue has expired, it is discarded and the
        next sound that has not expired is returned.
        """
        # We don't want to go through the entire sound queue more than once
        # in this method so keep track of the number of items we are
        # retrieving from the queue and exit when we have gone through
        # all items once.
        count = self._sound_queue.qsize()
        while count > 0:

            # Each item in the queue is a list containing the following items:
            #    0 (priority): The priority of the returned sound
            #    1 (exp_time): The time (in ticks) after which the sound expires and should not be played
            #    2 (sound): The Sound object ready for playback
            #    3 (settings): A dictionary of any additional settings for this sound's playback (ducking, etc.)

            try:
                next_sound = self._sound_queue.get_nowait()
                count -= 1
                if next_sound[2] is None:
                    continue
            except Empty:
                return None

            # If the sound is still loading and not expired, put it back in the queue
            if not next_sound[2].loaded and next_sound[2].loading and \
                    (next_sound[1] is None or next_sound[1] > time.time()):
                self._sound_queue.put(next_sound)
                self.log.debug("Re-queueing sound {}".format(next_sound))
            else:
                # Remove the queue entry from the list of sounds in the queue
                if next_sound in self._sound_queue_items[next_sound[2]]:
                    self._sound_queue_items[next_sound[2]].remove(next_sound)
                    if len(self._sound_queue_items[next_sound[2]]) == 0:
                        del self._sound_queue_items[next_sound[2]]

                # Return the next sound from the priority queue if it has not expired
                if not next_sound[1] or next_sound[1] > time.time():
                    return next_sound[2], -next_sound[0], next_sound[3]
                else:
                    self.log.debug("Discarding expired sound from queue {}".format(next_sound))

        return None

    def _remove_sound_from_queue(self, sound):
        """
        Removes a sound from the priority sound queue.
        Args:
            sound: The sound object to remove
        """

        # The sounds will not actually be removed from the priority queue because that
        # could corrupt the queue heap structure, but are simply set to None so they
        # will not be played.  After marking queue entry as None, the dictionary keeping
        # track of sounds in the queue is updated.
        if sound in self._sound_queue_items:
            for entry in self._sound_queue_items[sound]:
                entry[2] = None
            del self._sound_queue_items[sound]

    def play_sound(self, sound not None, **kwargs):
        """
        Plays a sound on the current track.
        Args:
            sound: The Sound object to play
            **kwargs: Optional additional arguments for overriding sound defaults
        """
        self.log.debug("play_sound - Processing sound '{}' for playback ({}).".format(sound.name, kwargs))

        settings = {}

        # Validate settings that can be overridden
        if 'priority' in kwargs and kwargs['priority'] is not None:
            priority = kwargs['priority']
        else:
            priority = sound.priority

        if 'loops' in kwargs and kwargs['loops'] is not None:
            settings['loops'] = kwargs['loops']
        else:
            settings['loops'] = sound.loops

        if 'max_queue_time' in kwargs:
            settings['max_queue_time'] = kwargs['max_queue_time']
        else:
            settings['max_queue_time'] = sound.max_queue_time

        if 'volume' in kwargs and kwargs['volume'] is not None:
            settings['volume'] = kwargs['volume']
        else:
            settings['volume'] = sound.volume

        # Volume is passed as a float 0.0 to 1.0, the audio library requires volume to be
        # an 8-bit unsigned int from 0 to MIX_MAX_VOLUME.
        settings['volume'] = <Uint8>min(max(settings['volume'] * MIX_MAX_VOLUME, 0), MIX_MAX_VOLUME)

        if settings['max_queue_time'] is None:
            exp_time = None
        else:
            exp_time = time.time() + settings['max_queue_time']

        # Make sure sound is loaded.  If not, we assume the sound is being loaded and we
        # add it to the queue so it will be picked up on the next loop.
        if not sound.loaded:
            # If the sound is not already loading, load it now
            if not sound.loading:
                sound.load()

            self.queue_sound(sound=sound,
                             priority=priority,
                             exp_time=exp_time,
                             settings=settings)
            self.log.debug("play_sound - Sound was not loaded and therefore has been "
                           "queued for playback.")
            return

        # If the sound can be played right away (available player) then play it.
        # Is there an available sound player?
        sound_player = self._get_sound_player_with_lowest_priority()
        player = sound_player[0]
        lowest_priority = sound_player[1]

        if lowest_priority is None:
            self.log.debug("play_sound - Sound player {} is available "
                           "for playback".format(player))
            # Play the sound using the available player
            return self._play_sound_on_sound_player(sound=sound,
                                                    player=player,
                                                    loops=settings['loops'],
                                                    volume=settings['volume'],
                                                    priority=priority)
        else:
            # All sound players are currently busy:
            self.log.debug("play_sound - No idle sound player is available.")
            self.log.debug("play_sound - Sound player {} is currently playing the sound with "
                           "the lowest priority ({}).".format(player, lowest_priority))

            # If the lowest priority of all the sounds currently playing is lower than
            # the requested sound, kill the lowest priority sound and replace it.
            if priority > lowest_priority:
                self.log.debug("play_sound - Sound priority ({}) is higher than the "
                               "lowest sound currently playing ({}). Forcing playback "
                               "on sound player {}.".format(priority, lowest_priority, player))
                return self._play_sound_on_sound_player(sound=sound,
                                                        player=player,
                                                        loops=settings['loops'],
                                                        volume=settings['volume'],
                                                        priority=priority,
                                                        force=True)
            else:
                # Add the requested sound to the priority queue
                self.queue_sound(sound=sound,
                                 priority=priority,
                                 exp_time=exp_time,
                                 settings=settings)
                self.log.debug("play_sound - Sound priority ({}) is less than or equal to the "
                               "lowest sound currently playing ({}). Sound will be queued "
                               "for playback.".format(priority, lowest_priority))

    def queue_sound(self, sound, priority, exp_time=None, settings=None):
        """Adds a sound to the queue to be played when a sound player becomes available.

        Args:
            sound: The Sound object to play.
            priority: The priority of the sound to be queued.
            exp_time: Real world time of when this sound will expire.  It will not play
                if the queue is freed up after it expires.  None indicates the sound
                never expires and will eventually be played.
            settings: Additional settings for the sound's playback.

        Note that this method will insert this sound into a position in the
        queue based on its priority, so highest-priority sounds are played
        first.
        """

        # Note the negative operator in front of priority since this queue
        # retrieves the lowest values first, and MPF uses higher values for
        # higher priorities.
        entry = [-priority, exp_time, sound, settings]
        self._sound_queue.put(entry)

        # Save the new entry in a dictionary of entries keyed by sound.  This
        # dictionary is used to remove pending sounds from the priority queue.
        if sound in self._sound_queue_items:
            self._sound_queue_items[sound].append(entry)
        else:
            self._sound_queue_items[sound] = [entry]

        self.log.debug("Queueing sound {}".format(entry))

    def stop_sound(self, sound not None):
        """
        Stops all instances of the specified sound immediately on the track. Any queued instances
        will be removed from the queue.
        Args:
            sound: The Sound to stop
        """

        SDL_LockMutex(self.mutex)

        for i in range(self.max_simultaneous_sounds):
            if self.attributes.sound_players[i].status != player_idle and self.attributes.sound_players[
                i].current.sound_id == sound.id:
                # Set stop sound event
                audio_message = self._get_available_audio_message()
                if audio_message != NULL:
                    audio_message.message = message_sound_stop
                    audio_message.sound_id = self.attributes.sound_players[i].current.sound_id
                    audio_message.track = self.number
                    audio_message.player = i
                    audio_message.time = SDL_GetTicks()
                else:
                    self.log.warning(
                        "All internal audio messages are currently "
                        "in use, could not stop sound {}".format(sound.name))

        # Remove any instances of the specified sound that are pending in the sound queue.
        self._remove_sound_from_queue(sound)

        SDL_UnlockMutex(self.mutex)

    def stop_sound_looping(self, sound not None):
        """
        Stops all instances of the specified sound on the track after they finish the current loop.
        Any queued instances of the sound will be removed.
        Args:
            sound: The Sound to stop
        """

        SDL_LockMutex(self.mutex)

        for i in range(self.max_simultaneous_sounds):
            if self.attributes.sound_players[i].status != player_idle and self.attributes.sound_players[
                i].current.sound_id == sound.id:
                # Set sound's loops_remaining variable to zero
                self.attributes.sound_players[i].current.loops_remaining = 0

        # Remove any instances of the specified sound that are pending in the sound queue.
        self._remove_sound_from_queue(sound)

        SDL_UnlockMutex(self.mutex)

    cdef int _get_available_sound_player(self):
        """
        Returns the index of the first available sound player or -1 if they are all busy.
        """
        SDL_LockMutex(self.mutex)

        for i in range(self.max_simultaneous_sounds):
            if self.attributes.sound_players[i].status == player_idle:
                SDL_UnlockMutex(self.mutex)
                return i

        SDL_UnlockMutex(self.mutex)
        return -1

    cdef tuple _get_sound_player_with_lowest_priority(self):
        """
        Retrieves the sound player currently with the lowest priority.

        Returns:
            A tuple consisting of the sound player index and the priority of
            the sound playing on that player (or None if the player is idle).

        """
        cdef int lowest_priority = 2147483647
        cdef int sound_player = -1

        SDL_LockMutex(self.mutex)

        for i in range(self.max_simultaneous_sounds):
            if self.attributes.sound_players[i].status == player_idle:
                SDL_UnlockMutex(self.mutex)
                return i, None
            elif self.attributes.sound_players[i].current.sound_priority < lowest_priority:
                lowest_priority = self.attributes.sound_players[i].current.sound_priority
                sound_player = i

        SDL_UnlockMutex(self.mutex)
        return i, lowest_priority

    cdef bint _play_sound_on_sound_player(self, sound, int player, int loops=0, Uint8 volume=MIX_MAX_VOLUME,
                                          int priority=0, bint force=False):
        """
        Plays a sound using the specified sound player
        """
        # Get the sound sample buffer container
        cdef MixChunkContainer mc = sound.container
        cdef int event_index
        cdef int envelope
        cdef AudioMessageContainer *audio_message
        cdef DuckingEnvelope *ducking_envelope
        cdef DuckingSettings *ducking_settings

        if not sound.loaded:
            self.log.debug("Specified sound is not loaded, could not "
                           "play sound {}".format(sound.name))
            return False

        # Make sure the player in range
        if player in range(self.max_simultaneous_sounds):
            SDL_LockMutex(self.mutex)
            # If the specified sound player is not idle do not play the sound if force is not set
            if self.attributes.sound_players[player].status != player_idle and not force:
                self.log.debug("All sound players are currently in use, "
                               "could not play sound {}".format(sound.name))
                SDL_UnlockMutex(self.mutex)
                return False

            # Set play sound event
            audio_message = self._get_available_audio_message()
            if audio_message != NULL:
                if self.attributes.sound_players[player].status != player_idle:
                    audio_message.message = message_sound_replace
                else:
                    # Reserve the sound player for this sound (it is no longer idle)
                    self.attributes.sound_players[player].status = player_pending
                    audio_message.message = message_sound_play

                audio_message.sound_id = sound.id
                audio_message.track = self.number
                audio_message.player = player
                audio_message.time = SDL_GetTicks()
                audio_message.data.play.chunk = mc.chunk
                audio_message.data.play.volume = volume
                audio_message.data.play.loops = loops
                audio_message.data.play.priority = priority

            else:
                self.log.warning("All internal audio messages are "
                               "currently in use, could not play sound {}"
                               .format(sound.name))

            # If the sound has a ducking envelope, apply it to the target track
            if sound.ducking is not None and sound.ducking.track is not None:
                # To convert between the number of samples and a buffer position (bytes), we need to
                # account for both the number of audio channels and number of bytes per sample (all
                # samples are 16 bits)
                samples_to_bytes_factor = self._audio_callback_data.audio_channels * BYTES_PER_SAMPLE

                # First get an available ducking envelope from the target track
                envelope = sound.ducking.track.get_available_ducking_envelope()
                if envelope == -1:
                    self.attributes.sound_players[player].current.sound_has_ducking = 0
                    self.log.warning("All ducking envelopes are "
                                     "currently in use in the target track, "
                                     "could not apply ducking for sound {}"
                                     .format(sound.name))
                else:
                    # Reserve the envelope
                    sound.ducking.track.set_ducking_envelope_stage(envelope, envelope_stage_delay)

                    # Set the ducking envelope settings for the sound player
                    self.attributes.sound_players[player].current.sound_has_ducking = 1
                    ducking_settings = cython.address(self.attributes.sound_players[player].current.ducking_settings)
                    ducking_settings.track = sound.ducking.track.number
                    ducking_settings.envelope_num = envelope
                    ducking_settings.attack_start_pos = sound.ducking.delay * samples_to_bytes_factor
                    ducking_settings.attack_duration = sound.ducking.attack * samples_to_bytes_factor
                    ducking_settings.attenuation_volume = <Uint8>(sound.ducking.attenuation * MIX_MAX_VOLUME)
                    ducking_settings.release_start_pos = mc.chunk.alen - (
                        sound.ducking.release_point * samples_to_bytes_factor)
                    ducking_settings.release_duration = sound.ducking.release * samples_to_bytes_factor

                    self.log.debug("Adding ducking settings to sound {}"
                                   .format(sound.name))
            else:
                self.attributes.sound_players[player].current.sound_has_ducking = 0

            SDL_UnlockMutex(self.mutex)

            self.log.debug("Sound {} is set to begin playback on player {} (loops={})"
                           .format(sound.name, player, loops))

            return True

        return False

    cdef AudioMessageContainer* _get_available_audio_message(self):
        """
        Returns a pointer to the first available audio event.
        If all audio messages are currently in use, NULL is returned.
        :return: The index of the first available audio event.  -1 if all
            are in use.
        """
        cdef AudioMessageContainer *event
        SDL_LockMutex(self.mutex)
        for i in range(MAX_AUDIO_MESSAGES):
            if self._audio_callback_data.messages[i].message == message_not_in_use:
                event = <AudioMessageContainer*> self._audio_callback_data.messages[i]
                SDL_UnlockMutex(self.mutex)
                return event

        SDL_UnlockMutex(self.mutex)
        return NULL

    def get_available_ducking_envelope(self):
        """
        Returns the index of the first available (idle) ducking envelope.
        If all ducking envelopes are currently in use, -1 is returned.
        :return: The index of the first available ducking envelope.  -1 if all
            are in use.
        """
        SDL_LockMutex(self.mutex)
        for i in range(MAX_TRACK_DUCKING_ENVELOPES):
            if self.attributes.ducking_envelopes[i].stage == envelope_stage_idle:
                SDL_UnlockMutex(self.mutex)
                return i

        SDL_UnlockMutex(self.mutex)
        return -1

    def set_ducking_envelope_stage(self, int envelope_num, int stage):
        """
        Sets the current stage for the specified ducking envelope
        Args:
            envelope_num: The ducking envelope number
            stage: The new envelope stage value
        Returns:
            A pointer to the specified ducking envelope
        """
        if envelope_num in range(MAX_TRACK_DUCKING_ENVELOPES):
            SDL_LockMutex(self.mutex)
            self.attributes.ducking_envelopes[envelope_num].stage = <DuckingEnvelopeStage>stage
            SDL_UnlockMutex(self.mutex)

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
        for player in range(self.max_simultaneous_sounds):
            status.append({
                "player": player,
                "status": Track.player_status_to_text(self.attributes.sound_players[player].status),
                "volume": self.attributes.sound_players[player].current.volume,
                "sound_id": self.attributes.sound_players[player].current.sound_id,
                "priority": self.attributes.sound_players[player].current.sound_priority,
                "loops": self.attributes.sound_players[player].current.loops_remaining,
                "has_ducking": self.attributes.sound_players[player].current.sound_has_ducking,
            })

            self.log.debug("Status - Player {}: Status={}, Sound={}, "
                           "Priority={}, Loops={}"
                           .format(player,
                                   Track.player_status_to_text(
                                       self.attributes.sound_players[player].status),
                                   self.attributes.sound_players[player].current.sound_id,
                                   self.attributes.sound_players[player].current.sound_priority,
                                   self.attributes.sound_players[player].current.loops_remaining))

        SDL_UnlockMutex(self.mutex)

        return status

    def get_sound_queue_count(self):
        """
        Gets the number of sounds currently in the track sound queue.
        Returns:
            Integer number of sounds currently in the track sound queue.
        """
        return self._sound_queue.qsize()

    def get_available_audio_message_count(self):
        """
        Gets the current count of available internal audio messages.  Used for debugging
        and testing.
        Returns:
            Integer number of internal audio messages available to be used.
        """
        available_event_count = 0
        SDL_LockMutex(self.mutex)
        for i in range(MAX_AUDIO_MESSAGES):
            if self._audio_callback_data.messages[i].message == message_not_in_use:
                available_event_count += 1
        SDL_UnlockMutex(self.mutex)
        return available_event_count

    def get_sound_players_in_use_count(self):
        """
        Gets the current count of sound players in use on the track.  Used for
        debugging and testing.
        Returns:
            Integer number of sound players currently in use on the track.
        """
        players_in_use_count = 0
        SDL_LockMutex(self.mutex)
        for i in range(self.max_simultaneous_sounds):
            if self.attributes.sound_players[i].status != player_idle:
                players_in_use_count += 1
        SDL_UnlockMutex(self.mutex)
        return players_in_use_count

    def sound_is_playing(self, sound):
        """Returns whether or not the specified sound is currently playing on the track"""
        SDL_LockMutex(self.mutex)
        for i in range(self.max_simultaneous_sounds):
            if self.attributes.sound_players[i].status != player_idle and \
                            self.attributes.sound_players[i].current.sound_id == sound.id:
                SDL_UnlockMutex(self.mutex)
                return True

        SDL_UnlockMutex(self.mutex)
        return False

    def sound_is_in_queue(self, sound):
        """Returns whether or not the specified sound is currently in the queue"""
        return sound in self._sound_queue_items

    @staticmethod
    def player_status_to_text(int status):
        """
        Converts a sound player status value into an equivalent text string
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
