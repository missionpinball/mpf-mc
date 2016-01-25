#cython: embedsignature=True, language_level=3
"""
Audio Library

This library requires both the SDL2 and SDL_Mixer libraries.
"""

__all__ = ('audio_interface_instance',
           'AudioInterface',
           'AudioException',
           'Track',
           'MixChunkContainer',
           )

__version_info__ = ('0', '1', '0-dev5')
__version__ = '.'.join(__version_info__)

from libc.stdlib cimport malloc, free, calloc
from libc.string cimport memset, memcpy
cimport cpython.pycapsule as pycapsule
import os.path
from time import time

from queue import PriorityQueue, Empty
import sys
from kivy.logger import Logger

include "audio_interface.pxi"


# ---------------------------------------------------------------------------
#    Maximum values for various audio engine settings
# ---------------------------------------------------------------------------
DEF MAX_TRACKS = 8
DEF MAX_SIMULTANEOUS_SOUNDS_DEFAULT = 8
DEF MAX_SIMULTANEOUS_SOUNDS_LIMIT = 32
DEF MAX_SOUND_EVENTS = 50

DEF MAX_AUDIO_VALUE_S16 = ((1 << (16 - 1)) - 1)
DEF MIN_AUDIO_VALUE_S16 = -(1 << (16 - 1))

# The global audio interface instance (there is only one instance)
cdef object audio_interface_instance = None


class AudioException(Exception):
    """Exception returned by the audio module
    """
    pass


cdef class AudioInterface:
    """
    The AudioInterface class provides a management wrapper around the SDL2 and SDL_Mixer
    libraries.
    """
    cdef int sample_rate
    cdef int audio_channels
    cdef int buffer_samples
    cdef int buffer_size
    cdef int supported_formats
    cdef int mixer_channel
    cdef list tracks

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

    def __init__(self, rate=44100, channels=2, buffer_samples=4096):
        """
        Initializes the AudioInterface.
        Args:
            rate: The audio sample rate used in the library
            channels: The number of channels to use (1=mono, 2=stereo)
            buffer_samples: The audio buffer size to use (in number of samples, must be power of two)
        """

        # Initialize threading in the extension library and acquire the Python global interpreter lock
        PyEval_InitThreads()

        # Make sure buffer samples is a power of two (required by SDL2)
        if not AudioInterface.power_of_two(buffer_samples):
            Logger.error('AudioInterface: Buffer samples is required to be a power of two')
            raise AudioException("Unable to initialize Audio Interface: "
                                 "Buffer samples is required to be a power of two")

        # Initialize the SDL audio system
        if SDL_Init(SDL_INIT_AUDIO) < 0:
            Logger.error('SDL_Init: %s' % SDL_GetError())
            raise AudioException('Unable to initialize SDL (SDL_Init call failed: %s)' % SDL_GetError())

        # Initialize the SDL_Mixer library to establish the output audio format and encoding
        # (sample rate, bit depth, buffer size)
        if Mix_OpenAudio(rate, AUDIO_S16SYS, channels, buffer_samples):
            Logger.error('Mix_OpenAudio: %s' % SDL_GetError())
            raise AudioException('Unable to open audio for output (Mix_OpenAudio failed: %s)' % SDL_GetError())

        Logger.info("AudioInterface: Initialized AudioInterface {}".format(AudioInterface.get_version()))
        Logger.info("AudioInterface: Loaded {}".format(AudioInterface.get_sdl_version()))
        Logger.info("AudioInterface: Loaded {}".format(AudioInterface.get_sdl_mixer_version()))

        # Lock SDL from calling the audio callback functions
        SDL_LockAudio()

        # Determine the actual audio format in use by the opened audio device.  This may or may not match
        # the parameters used to initialize the audio interface.
        self.buffer_samples = buffer_samples
        Logger.info('AudioInterface: requested {} {} {}'.format(rate, channels, buffer_samples))
        Mix_QuerySpec(&self.sample_rate, NULL, &self.audio_channels)
        Logger.info('AudioInterface: received {} {} {}'
                    .format(self.sample_rate, self.audio_channels, self.buffer_samples))

        # Set the size of the track audio buffers (samples * channels * 2 bytes/sample) for 16-bit audio
        self.buffer_size = self.buffer_samples * self.audio_channels * 2

        # Allocate memory for the audio callback data structure
        self.audio_callback_data = <AudioCallbackData*>calloc(1, sizeof(AudioCallbackData))

        # Initialize the audio callback data structure
        self.audio_callback_data.sample_rate = self.sample_rate
        self.audio_callback_data.audio_channels = self.audio_channels
        self.audio_callback_data.master_volume = 0
        self.audio_callback_data.track_count = 0
        self.audio_callback_data.tracks = <TrackAttributes**>calloc(MAX_TRACKS, sizeof(TrackAttributes*))
        self.audio_callback_data.mutex = SDL_CreateMutex()

        # Initialize the supported SDL_Mixer library formats
        self.supported_formats = Mix_Init(MIX_INIT_FLAC | MIX_INIT_OGG)

        self._initialize_silence()
        self._initialize_audio_callback()

        # Unlock the SDL audio callback functions
        SDL_UnlockAudio()

        self.tracks = []

    def _initialize_silence(self):
        """
        Initializes and generates an audio chunk/sample containing silence (used to play on each
        track since each track in SDL_Mixer must play something to call its effects callback
        functions which are used in this library to perform the actual sound generation/mixing)
        """
        # Create the audio buffer containing silence
        cdef Uint8 *silence = NULL
        cdef Uint32 length = self.buffer_size
        silence = <Uint8 *>calloc(1, length)

        # Instruct SDL_Mixer to load the silence into a chunk
        self.raw_chunk_silence = Mix_QuickLoad_RAW(silence, length)
        if self.raw_chunk_silence == NULL:
            raise AudioException('Unable to load generated silence sample required for playback')

    def _initialize_audio_callback(self):
        # Set the number of channels to mix (will cause existing channels to be stopped and restarted if playing)
        # This is an SDL_Mixer library function call.
        channels = Mix_AllocateChannels(1)
        Logger.debug("SDL_Mixer: Allocated {} channel(s)".format(channels))
        self.mixer_channel = 0

        # Setup callback function for mixer channel depending upon the audio format used
        cdef Mix_EffectFunc_t audio_callback_fn = AudioInterface.audio_callback

        # Register the audio callback function that will perform the actual mixing of sounds.
        # A pointer to the audio callback data is passed to the callback function that contains
        # all necessary data to perform the playback and mixing of sounds.
        # This is an SDL_Mixer library function call.
        Mix_RegisterEffect(self.mixer_channel, audio_callback_fn, NULL, <void *>self.audio_callback_data)

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
        global audio_interface_instance

        # If instance has already been initialized, return it (we can't have more than one
        # audio interface instance).
        if audio_interface_instance is not None:
            return audio_interface_instance

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
    def get_version():
        """
        Retrieves the current version of the audio interface library
        :return: Audio interface library version string
        """
        return __version__

    @staticmethod
    def get_sdl_version():
        """
        Returns the version of the SDL library
        :return: SDL library version string
        """
        cdef SDL_version version
        SDL_GetVersion(&version)
        return 'SDL {}.{}.{}'.format(version.major, version.minor, version.patch)

    @staticmethod
    def get_sdl_mixer_version():
        """
        Returns the version of the dynamically linked SDL_Mixer library
        :return: SDL_Mixer library version string
        """
        cdef const SDL_version *version =  Mix_Linked_Version()
        return 'SDL_Mixer {}.{}.{}'.format(version.major, version.minor, version.patch)

    @staticmethod
    def supported_extensions():
        """
        Get the file extensions that are supported by the audio interface.
        Returns:
            A list of file extensions supported.
        """
        return ["wav", "flac", "ogg"]

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
        return Mix_Playing(self.mixer_channel) == 1

    def enable(self, int fade_sec=0):
        """
        Enables audio playback with a fade in (begins audio processing)
        Args:
            fade_sec:  The number of seconds over which to fade in the audio
        """
        cdef int fade_ms = 0
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
        SDL_LockAudio()
        if fade_sec > 0:
            fade_ms = fade_sec // 1000
            Mix_FadeOutChannel(self.mixer_channel, fade_ms)
        else:
            Mix_HaltChannel(self.mixer_channel)

        SDL_UnlockAudio()

    @staticmethod
    def get_max_tracks():
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
            Logger.error("Add track failed: The maximum number of tracks ({}) has been reached.".format(MAX_TRACKS))
            return None

        # Make sure track name does not already exist (no duplicates allowed)
        name = name.lower()
        for track in self.tracks:
            if name == track.name:
                Logger.error("Add track failed: The track name '{}' already exists.".format(name))
                return None

        # Make sure audio callback function cannot be called while we are changing the track data
        SDL_LockAudio()

        # Create the new track
        new_track = Track(name,
                          track_num,
                          # Wrap the mutex pointer in a PyCapsule to pass it into the Track constructor
                          pycapsule.PyCapsule_New(self.audio_callback_data.mutex, NULL, NULL),
                          self.buffer_size,
                          max_simultaneous_sounds,
                          volume)
        self.tracks.append(new_track)

        # Update audio callback data with new track
        self.audio_callback_data.track_count = len(self.tracks)
        self.audio_callback_data.tracks[track_num] = new_track.attributes

        # Allow audio callback function to be called again
        SDL_UnlockAudio()

        Logger.info("The '{}' track has successfully been created.".format(name))

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
        cdef char* c_file_name = py_byte_file_name

        # Attempt to load the file
        cdef Mix_Chunk *chunk = Mix_LoadWAV(c_file_name)
        if chunk == NULL:
            Logger.error("AudioInterface: Unable to load sound from source file '{}' - {}"
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
            Mix_FreeChunk(mc.chunk)
            mc.chunk = NULL

    def stop_sound(self, sound not None):
        """
        Stops all instances of the specified sound immediately on all tracks.
        Args:
            sound: The Sound to stop
        """
        for track in self.tracks:
            track.stop_sound(sound)

    @staticmethod
    cdef void audio_callback(int channel, void *output_buffer, int length, void *data) nogil:
        """
        Audio callback function (called from SDL_Mixer).
        Args:
            channel: The SDL_Mixer channel number (corresponds to the audio interface channel number)
            output_buffer: The SDL_Mixer audio buffer for the mixer channel to process
            length: The length (bytes) of the audio buffer
            data: A pointer to the Track class for the channel
        """

        if data == NULL:
            return

        # SDL_Mixer channel should already be playing 'silence', a silent sample generated in memory.
        # This is so SDL_Mixer thinks the channel is active and will call the channel callback
        # function which is used to read and mix the actual source audio.
        cdef AudioCallbackData *callback_data = <AudioCallbackData*>data

        # Lock the mutex to ensure no audio data is changed during the playback processing
        # (multi-threaded protection)
        SDL_LockMutex(callback_data.mutex)

        # Loop over tracks, mixing the playing sounds into the track's audio buffer
        for track_num in range(callback_data.track_count):

            # Zero out track buffer (start with silence)
            memset(callback_data.tracks[track_num].buffer, 0, length)

            # Mix any playing sounds into the track buffer
            mix_sounds_to_track(callback_data.tracks[track_num],
                                callback_data.tracks[track_num].buffer,
                                length)

        # Loop over tracks again, mixing down tracks to the master output buffer
        for track_num in range(callback_data.track_count):
            # Apply ducking envelopes to track audio buffer

            # Apply track volume and mix to output buffer
            mix_track_to_output(<Uint8*>callback_data.tracks[track_num].buffer,
                                callback_data.tracks[track_num].volume,
                                <Uint8*>output_buffer,
                                length)


        # Apply master volume to output buffer

        # Unlock the mutex since we are done accessing the audio data
        SDL_UnlockMutex(callback_data.mutex)


cdef void mix_sounds_to_track(TrackAttributes *track, void* buffer, int buffer_size) nogil:
    """
    Mixes any sounds that are playing on the specified track into the specified audio buffer.
    Args:
        track: A pointer to the TrackAttributes data structure for the track
        buffer: A pointer to the audio buffer to mix the playing sounds into
        buffer_size: The length of the destination audio buffer (bytes)
    """
    if track == NULL:
        return

    # Get the current clock from SDL (it is used for the audio timing master)
    cdef Uint32 sdl_ticks = SDL_GetTicks()

    # Setup source (sound) and destination (track) buffer pointers/values
    cdef Uint8 *sound_buffer
    cdef Uint8 *output_buffer = <Uint8*>buffer

    cdef Sample16Bit sound_sample
    cdef Sample16Bit output_sample
    cdef int temp_sample

    cdef int event_index
    cdef int index

    # Loop over track sound players
    for player in range(track.max_simultaneous_sounds):

        # If the player is idle, there is nothing to do so move on to the next player
        if track.sound_players[player].status is player_idle:
            continue

        # Check if player has a sound pending playback (ready to start)
        if track.sound_players[player].status is player_pending:
            # Sound ready to start playback, send event notification and set status to playing
            event_index = get_open_sound_event_on_track(track)
            if event_index != -1:
                track.events[event_index].event = event_sound_start
                track.events[event_index].track_num = track.track_num
                track.events[event_index].player = player
                track.events[event_index].sound_id = track.sound_players[player].sound_id
                track.events[event_index].time = sdl_ticks

            # TODO: Log error if events are full

            track.sound_players[player].status = player_playing

        # If audio playback object is playing, add it's samples to the output buffer (scaled by sample volume)
        if track.sound_players[player].status is player_playing \
                and track.sound_players[player].volume > 0:

            # Get source sound buffer (read one byte at a time, bytes will be combined into a
            # 16-bit sample value before being mixed)
            sound_buffer = <Uint8*>track.sound_players[player].chunk.abuf

            # Loop over destination buffer, mixing in the source sample
            index = 0
            while index < buffer_size:

                # Get sound sample (2 bytes), combine into a 16-bit value and apply sound volume
                sound_sample.bytes.byte0 = sound_buffer[track.sound_players[player].sample_pos]
                sound_sample.bytes.byte1 = sound_buffer[track.sound_players[player].sample_pos + 1]
                sound_sample.value = (sound_sample.value * track.sound_players[player].volume) / MIX_MAX_VOLUME

                # Get sample (2 bytes) already in the output buffer and combine into 16-bit value
                output_sample.bytes.byte0 = output_buffer[index]
                output_sample.bytes.byte1 = output_buffer[index + 1]

                # Calculate the new output sample (mix the existing output sample with
                # the new source sound).  The temp sample is a 32-bit value to avoid overflow.
                temp_sample = output_sample.value + sound_sample.value

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

                # Advance the source sample pointer to the next sample (2 bytes)
                track.sound_players[player].sample_pos += 2

                # Advance the output buffer pointer to the next sample (2 bytes)
                index += 2

                # Check if we are at the end of the source sample buffer (loop if applicable)
                if track.sound_players[player].sample_pos > track.sound_players[player].chunk.alen:
                    if track.sound_players[player].loops_remaining > 0:
                        # At the end and still loops remaining, loop back to the beginning
                        track.sound_players[player].loops_remaining -= 1
                        track.sound_players[player].sample_pos = 0
                    elif track.sound_players[player].loops_remaining == 0:
                        # At the end and not looping, the sample has finished playing
                        track.sound_players[player].status = player_finished
                        track.sound_players[player].sample_pos = 0
                        break
                    else:
                        # Looping infinitely, loop back to the beginning
                        track.sound_players[player].sample_pos = 0

cdef void mix_track_to_output(Uint8 *track_buffer, int track_volume, Uint8 *output_buffer, int buffer_size) nogil:

    cdef Sample16Bit track_sample
    cdef Sample16Bit output_sample

    cdef int temp_sample
    cdef int index

    index = 0
    while index < buffer_size:

        # Get sound sample (2 bytes), combine into a 16-bit value and apply sound volume
        track_sample.bytes.byte0 = track_buffer[index]
        track_sample.bytes.byte1 = track_buffer[index + 1]
        track_sample.value = track_sample.value * track_volume / MIX_MAX_VOLUME

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

        index += 2

cdef int get_open_sound_event_on_track(TrackAttributes* track) nogil:
    """
    Returns the index of the first available sound event on the supplied track.
    If all sound events are currently in use, -1 is returned.
    :param track:
    :return: The index of the first available sound event.  -1 if all are in use.
    """
    if track == NULL:
        return -1

    for i in range(MAX_SOUND_EVENTS):
        if track.events[i].event == event_none:
            return i

    return -1


cdef class Track:
    """
    Track class
    """
    # The name of the track
    cdef str _name
    cdef object _sound_queue
    cdef float _volume
    cdef SDL_mutex *mutex

    # Track attributes need to be stored in a C struct in order for them to be accessible in
    # the SDL callback functions without the GIL (for performance reasons).  The TrackAttributes
    # struct is allocated during construction and freed during destruction.
    cdef TrackAttributes *attributes

    def __init__(self, str name, int track_num, object mutex, int buffer_size,
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
        self.mutex = <SDL_mutex*>pycapsule.PyCapsule_GetPointer(mutex, NULL)

        self._sound_queue = PriorityQueue()

        # Make sure the number of simultaneous sounds is within the allowable range
        if max_simultaneous_sounds > MAX_SIMULTANEOUS_SOUNDS_LIMIT:
            Logger.warning("AudioInterface: The maximum number of simultaneous sounds per track is {}"
                           .format(MAX_SIMULTANEOUS_SOUNDS_LIMIT))
            max_simultaneous_sounds = MAX_SIMULTANEOUS_SOUNDS_LIMIT
        elif max_simultaneous_sounds < 1:
            Logger.warning("AudioInterface: The minimum number of simultaneous sounds per track is 1")
            max_simultaneous_sounds = 1

        # Allocate memory for the track attributes
        self.attributes = <TrackAttributes*>calloc(1, sizeof(TrackAttributes))
        self.attributes.track_num = track_num
        self.attributes.max_simultaneous_sounds = max_simultaneous_sounds
        self.attributes.buffer = calloc(buffer_size, sizeof(void*))
        self.attributes.buffer_size = buffer_size
        Logger.info("Track {}: allocated track audio buffer ({} bytes)".format(name, buffer_size))
        self.volume = volume
        self._name = name

        # Allocate memory for the sound player structs needed for the desired number of
        # simultaneous sounds that can be played on the track.
        self.attributes.sound_players = <SoundPlayer*>calloc(self.max_simultaneous_sounds, sizeof(SoundPlayer))

        # Initialize sound player attributes
        for i in range(self.max_simultaneous_sounds):
            self.attributes.sound_players[i].chunk = NULL
            self.attributes.sound_players[i].status = player_idle
            self.attributes.sound_players[i].loops_remaining = 0
            self.attributes.sound_players[i].start_time = 0
            self.attributes.sound_players[i].samples_elapsed = 0
            self.attributes.sound_players[i].volume = 0
            self.attributes.sound_players[i].sample_pos = 0
            self.attributes.sound_players[i].sound_id = 0
            self.attributes.sound_players[i].sound_priority = 0

        # Initialize sound events
        self.attributes.events = <SoundEventData*>calloc(MAX_SOUND_EVENTS, sizeof(SoundEventData))
        for i in range(MAX_SOUND_EVENTS):
            self.attributes.events[i].event = event_none
            self.attributes.events[i].track_num = 0
            self.attributes.events[i].player = 0
            self.attributes.events[i].sound_id = 0
            self.attributes.events[i].time = 0

    def __dealloc__(self):

        # Free the attributes and other allocated memory
        if self.attributes != NULL:
            if self.attributes.buffer != NULL:
                free(self.attributes.buffer)
                self.attributes.buffer = NULL

            if self.attributes.sound_players != NULL:
                free(self.attributes.sound_players)
                self.attributes.sound_players = NULL

            if self.attributes.events != NULL:
                free(self.attributes.events)
                self.attributes.events = NULL

            free(self.attributes)
            self.attributes = NULL

    def __repr__(self):
        return '<Track.{}({})>'.format(self.name, self.number)

    property name:
        def __get__(self):
            return self._name

    property volume:
        def __get__(self):
            return self._volume

        def __set__(self, float value):
            if self.attributes != NULL:
                value = max(min(value, 1.0), 0.0)
                self._volume = value
                # Volume used in SDL_Mixer is an integer between 0 and MIX_MAX_VOLUME (0 to 128)
                self.attributes.volume = int(self._volume * MIX_MAX_VOLUME)

    @property
    def number(self):
        if self.attributes != NULL:
            return self.attributes.track_num
        else:
            return -1

    @property
    def max_simultaneous_sounds(self):
        if self.attributes != NULL:
            return self.attributes.max_simultaneous_sounds
        else:
            return 0

    cdef int get_idle_sound_player(self):
        """
        Returns the index of the first idle sound player on the track.  If all
        players are currently busy playing, -1 is returned.
        """
        for index in range(self.max_simultaneous_sounds):
            if self.attributes.sound_players[index].status == player_idle:
                return index

        return -1

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
        next_sound = None
        while next_sound is None:
            try:
                next_sound = self._sound_queue.get_nowait()
            except Empty:
                return None

            # Each item in the queue is a list containing the following items:
            #    0 (priority): The priority of the returned sound
            #    1 (sound): The Sound object ready for playback
            #    2 (exp_time): The time (in ticks) after which the sound expires and should not be played
            #    3 (settings): A dictionary of any additional settings for this sound's playback (ducking, etc.)

            # Return the next sound from the priority queue if it has not expired
            if not next_sound[2] or next_sound[2] > time.time():
                return next_sound[1], -next_sound[0], next_sound[3]
            else:
                next_sound = None

    def play_sound(self, sound not None, int priority, **settings):
        """
        Plays a sound on the current track.
        Args:
            sound: Sound to play
            priority: The relative priority of the sound
            **settings: Optional additional settings for playing the sound
        """

        # Make sure sound is loaded.  If not, we assume the sound is being loaded and we
        # add it to the queue so it will be picked up on the next loop.
        if not sound.loaded:
            self.queue_sound(sound, priority, **settings)
            Logger.debug("play_sound: Sound was not loaded and therefore was queued for playback.")
            return

        # If the sound can be played right away (available player) then play it.
        # Is there an available sound player?
        player = self._get_available_sound_player()
        if player >= 0:
            Logger.debug("play_sound: Sound player {} is available for playback".format(player))
            # Play the sound using the available player
            self._play_sound_on_sound_player(sound, player)
        else:
            # No available sound players:
            Logger.debug("play_sound: No sound player is available.")
            #     1) If the lowest priority of all the sounds currently playing is lower than
            #        the requested sound, kill the lowest priority sound and replace it.
            #     2) Add the requested sound to the priority queue
            pass


        # Add the sound to the queue
        # TODO: Implement me

    def queue_sound(self, sound, priority, exp_time=None, **settings):
        """Adds a sound to the queue to be played when a sound player becomes available.

        Args:
            sound: The Sound object to play.
            priority: The priority of the sound to be queued.
            exp_time: Real world time of when this sound will expire.  It will not play
                if the queue is freed up after it expires.  None indicates the sound
                never expires and will eventually be played.
            **settings: Additional settings for the sound's playback.

        Note that this method will insert this sound into a position in the
        queue based on its priority, so highest-priority sounds are played
        first.
        """

        # Note the negative operator in front of priority since this queue
        # retrieves the lowest values first, and MPF uses higher values for
        # higher priorities.
        self._sound_queue.put([-priority, sound, exp_time, settings])

    def stop_sound(self, sound not None):
        """
        Stops all instances of the specified sound immediately on the track.
        Args:
            sound: The Sound to stop
        """

        SDL_LockMutex(self.mutex)

        for i in range(self.max_simultaneous_sounds):
            if self.attributes.sound_players[i].status != player_idle \
                    and self.attributes.sound_players[i].sound_id == sound.id:
                self.attributes.sound_players[i].status = player_finished

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

    cdef int _get_sound_player_with_lowest_priority(self):
        """
        Retrieves the sound player currently with the lowest priority.

        Returns:
            A tuple consisting of the sound player index and the priority of
            the sound playing on that player (or -1 if the player is idle).

        """
        cdef int lowest_priority = sys.maxsize
        cdef int sound_player = -1

        SDL_LockMutex(self.mutex)

        for i in range(self.max_simultaneous_sounds):
            if self.attributes.sound_players[i].status == player_idle:
                SDL_UnlockMutex(self.mutex)
                return i, -1
            elif self.attributes.sound_players[i].sound_priority < lowest_priority:
                lowest_priority = self.attributes.sound_players[i].sound_priority
                sound_player = i

        SDL_UnlockMutex(self.mutex)
        return i

    cdef bint _play_sound_on_sound_player(self, sound, int player, int loops=0, int priority=0, force=True):
        """
        Plays a sound using the specified sound player
        """
        # Get the sound sample buffer container
        cdef MixChunkContainer mc = sound.container

        # Make sure the player in range
        if player in range(self.max_simultaneous_sounds):
            SDL_LockMutex(self.mutex)
            # If the specified sound player is not idle do not play the sound if force is not set
            if self.attributes.sound_players[player].status != player_idle and not force:
                SDL_UnlockMutex(self.mutex)
                Logger.debug("_play_sound_on_sound_player: Sound player is not available, cannot play sound.")
                return False

            # Play the sound
            self.attributes.sound_players[player].chunk = mc.chunk
            self.attributes.sound_players[player].status = player_pending
            self.attributes.sound_players[player].volume = mc.chunk.volume
            self.attributes.sound_players[player].loops_remaining = loops
            self.attributes.sound_players[player].start_time = SDL_GetTicks()
            self.attributes.sound_players[player].samples_elapsed = 0
            self.attributes.sound_players[player].sample_pos = 0
            self.attributes.sound_players[player].sound_id = sound.id
            self.attributes.sound_players[player].sound_priority = priority
            # TODO: Set other sound player attributes

            SDL_UnlockMutex(self.mutex)

            Logger.debug("_play_sound_on_sound_player: Sound is playing")

            return True

        return False


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
        return self.chunk != NULL


class DuckingEnvelope(object):

    def __init__(self):
        self.track = None
        self.delay = 0
        self.attack = 0
        self.attenuation = 1.0
        self.release_point = 0
        self.release = 0
