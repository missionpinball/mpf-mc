#cython: embedsignature=True, language_level=3

"""
Pinaudio Python extension library. Provides cross-platform audio playback
functions designed for pinball machines, but would likely work well in many
other gaming genres.

Loosely based on the Kivy Audiostream open source Python extension library:
https://github.com/kivy/audiostream

Requires SDL2 and SDL_Mixer libraries (https://www.libsdl.org/)

============================

"""

__all__ = (
    'get_audio_output',
    'get_version',
    'get_sdl_version',
    'get_sdl_mixer_version',
    'AudioOutput',
    'AudioException')

DEF SDL_INIT_AUDIO = 0x10
DEF MIX_CHANNELS_MAX = 8
DEF AUDIO_S16SYS = 0x8010
DEF AUDIO_S8 = 0x8008
DEF MIX_MAX_VOLUME = 128

DEF MAX_AUDIO_VALUE_S16 = ((1 << (16 - 1)) - 1)
DEF MIN_AUDIO_VALUE_S16 = -(1 << (16 - 1))
DEF MAX_AUDIO_VALUE_S8 = ((1 << (8 - 1)) - 1)
DEF MIN_AUDIO_VALUE_S8 = -(1 << (8 - 1))

DEF MAX_AUDIO_EVENTS = 50

from libc.stdlib cimport malloc, free, calloc
from libc.string cimport memset, memcpy
from libc.math cimport sin

cimport cpython.pycapsule as pycapsule
from .version import __version__

include "common.pxi"

class AudioException(Exception):
    """Exception returned by the PinAudio module
    """
    pass


cdef void mix_track_callback_s8(int channel, void *stream, int length, void *userdata) nogil:
    """
    SDL Callback function used to mix playing 8-bit sounds to a track/channel.
    Ducking envelopes are also processed and applied in this function.
    :param channel: The SDL_Mixer channel number used for the track
    :param stream: A pointer to the track/channel audio buffer
    :param length: The track/channel audio buffer length
    :param userdata: A pointer to the MixerChannel struct for the track
    :return: None
    """
    if userdata == NULL:
        return

    # Mixer channel should already be playing 'silence', a silent sample generated in memory.
    # This is so SDL_Mixer thinks the channel is active and will call the channel callback
    # function which is used to read and mix the source audio.
    cdef MixerChannel *mix_channel = <MixerChannel*>userdata

    # Attempt to lock the track/channel mutex while performing operations on the track/channel
    if SDL_LockMutex(mix_channel.mutex) != 0:
        return

    # Get the current clock from SDL (it is used for the audio timing master)
    cdef uint32_t sdl_ticks = SDL_GetTicks()

    # Setup source and destination buffer pointers/values
    cdef int8_t *dst8
    dst8 = <int8_t*>stream
    cdef int8_t *src8
    cdef int8_t src_sample

    cdef int dst_sample

    # Loop over all channel audio playback objects
    for i in range(mix_channel.max_simultaneous_sounds):
        # Check if player has a sound pending playback (ready to start)
        if mix_channel.sample_players[i].status is player_pending:
            # Sound ready to start playback, send notification and set status to playing
            # TODO: set notification that a sound has started playing
            mix_channel.sample_players[i].status = player_playing

            with gil:
                print("Callback: Changing status from pending to playing (sample {} on channel {} with player {})".format(mix_channel.sample_players[i].sample_number, channel, i))

        # If audio playback object is playing, add it's samples to the output buffer (scaled by sample volume)
        if mix_channel.sample_players[i].status is player_playing and mix_channel.sample_players[i].volume > 0:

            # Get source sample buffer
            src8 = <int8_t*>mix_channel.sample_players[i].chunk.abuf

            with gil:
                print("Callback: Playing (sample {} on channel {} with player {})".format(mix_channel.sample_players[i].sample_number, channel, i))

            # Loop over destination buffer one byte at a time, mixing in the source sample
            for index in range(length):

                # Get source sample byte and apply sample volume
                src_sample = src8[mix_channel.sample_players[i].sample_pos]
                src_sample = (src_sample * mix_channel.sample_players[i].volume) / MIX_MAX_VOLUME

                # Calculate the new destination sample (mix in source sample)
                dst_sample = dst8[index] + src_sample

                # Apply clipping to destination sample
                if dst_sample > MAX_AUDIO_VALUE_S8:
                    dst8[index] = MAX_AUDIO_VALUE_S8
                elif dst_sample < MIN_AUDIO_VALUE_S8:
                    dst8[index] = MIN_AUDIO_VALUE_S8
                else:
                    dst8[index] = dst_sample

                # Advance the source sample pointer to the next sample (byte)
                mix_channel.sample_players[i].sample_pos += 1

                # Check if we are at the end of the source sample buffer (loop if applicable)
                if mix_channel.sample_players[i].sample_pos > mix_channel.sample_players[i].chunk.alen:
                    if mix_channel.sample_players[i].loops_remaining > 0:
                        # At the end and still loops remaining, loop back to the beginning
                        mix_channel.sample_players[i].loops_remaining -= 1
                        mix_channel.sample_players[i].sample_pos = 0
                    if mix_channel.sample_players[i].loops_remaining == 0:
                        # At the end and not looping, the sample has finished playing
                        mix_channel.sample_players[i].status = player_finished
                        with gil:
                            print("Callback: Changing status from playing to finished (sample {} on channel {} with player {})".format(mix_channel.sample_players[i].sample_number, channel, i))
                        break
                    else:
                        # Looping infinitely, loop back to the beginning
                        mix_channel.sample_players[i].sample_pos = 0

        # Check if the sound has finished
        if mix_channel.sample_players[i].status is player_finished:
            # Sound has finished, send notification and set player to idle status
            # TODO: send sound finished playing notification
            mix_channel.sample_players[i].status = player_idle

            with gil:
                print("Callback: Changing status from finished to idle (sample {} on channel {} with player {})".format(mix_channel.sample_players[i].sample_number, channel, i))

    # Apply channel volume

    # Apply channel envelope (if applicable)

    # Release the lock on the channel mutex
    SDL_UnlockMutex(mix_channel.mutex)

cdef void mix_track_callback_s16sys(int channel, void *stream, int length, void *userdata) nogil:
    """
    SDL Callback function used to mix playing 16-bit sounds to a track/channel.
    Ducking envelopes are also processed and applied in this function.
    :param channel: The SDL_Mixer channel number used for the track
    :param stream: A pointer to the track/channel audio buffer
    :param length: The track/channel audio buffer length
    :param userdata: A pointer to the MixerChannel struct for the track
    :return: None
    """
    if userdata == NULL:
        return

    # Mixer channel should already be playing 'silence', a silent sample generated in memory.
    # This is so SDL_Mixer thinks the channel is active and will call the channel callback
    # function which is used to read and mix the source audio.
    cdef MixerChannel *mix_channel = <MixerChannel*>userdata

    # Attempt to lock the track/channel mutex while performing operations on the track/channel
    if SDL_LockMutex(mix_channel.mutex) != 0:
        return

    # Get the current clock from SDL (it is used for the audio timing master)
    cdef uint32_t sdl_ticks = SDL_GetTicks()

    # Setup source and destination buffer pointers/values
    cdef int8_t *src

    cdef Sample16Bit src_sample
    cdef Sample16Bit channel_sample

    cdef int16_t *dst16
    dst8 = <int8_t*>stream

    cdef int temp_sample
    cdef Sample16Bit dst_sample

    cdef int index

    # Loop over all channel audio playback objects
    for player in range(mix_channel.max_simultaneous_sounds):

        # If the player is idle, there is nothing to do so move on to the next player
        if mix_channel.sample_players[player].status is player_idle:
            continue

        # Check if player has a sound pending playback (ready to start)
        if mix_channel.sample_players[player].status is player_pending:
            # Sound ready to start playback, send notification and set status to playing
            event_index = get_first_available_audio_event_on_mixer_channel(mix_channel)
            if event_index != -1:
                mix_channel.events[event_index].event = event_sound_start
                mix_channel.events[event_index].channel = channel
                mix_channel.events[event_index].player = player
                mix_channel.events[event_index].sample_number = mix_channel.sample_players[player].sample_number

            # TODO: Log error if events are full

            mix_channel.sample_players[player].status = player_playing

        # If audio playback object is playing, add it's samples to the output buffer (scaled by sample volume)
        if mix_channel.sample_players[player].status is player_playing \
                and mix_channel.sample_players[player].volume > 0:

            # Get source sample buffer (read one byte at a time, bytes will be combined into a
            # 16-bit sample value before being mixed)
            src = <int8_t*>mix_channel.sample_players[player].chunk.abuf

            # Loop over destination buffer, mixing in the source sample
            index = 0
            while index < length:

                # Get source sample (2 bytes), combine into a 16-bit value and apply sample volume
                src_sample.bytes.byte1 = src[mix_channel.sample_players[player].sample_pos]
                src_sample.bytes.byte2 = src[mix_channel.sample_players[player].sample_pos + 1]
                src_sample.value = (src_sample.value * mix_channel.sample_players[player].volume) / MIX_MAX_VOLUME

                # Get sample (2 bytes) already in the destination buffer and combine into 16-bit value
                channel_sample.bytes.byte1 = dst8[index]
                channel_sample.bytes.byte2 = dst8[index + 1]

                # Calculate the new destination sample (mix the existing destination sample with
                # the new source sample).  The temp sample is a 32-bit value to avoid overflow.
                temp_sample = channel_sample.value + src_sample.value

                # Clip the temp sample back to a 16-bit value (will cause distortion if samples
                # on channel are too loud)
                if temp_sample > MAX_AUDIO_VALUE_S16:
                    temp_sample = MAX_AUDIO_VALUE_S16
                elif temp_sample < MIN_AUDIO_VALUE_S16:
                    temp_sample = MIN_AUDIO_VALUE_S16

                # Write the new destination sample back to the destination buffer (from a 32-bit
                # back to a 16-bit value that we know is in range)
                dst_sample.value = temp_sample
                dst8[index] = dst_sample.bytes.byte1
                dst8[index + 1] = dst_sample.bytes.byte2

                # Advance the source sample pointer to the next sample (2 bytes)
                mix_channel.sample_players[player].sample_pos += 2

                # Advance the destination buffer pointer to the next sample (2 bytes)
                index += 2

                # Check if we are at the end of the source sample buffer (loop if applicable)
                if mix_channel.sample_players[player].sample_pos > mix_channel.sample_players[player].chunk.alen:
                    if mix_channel.sample_players[player].loops_remaining > 0:
                        # At the end and still loops remaining, loop back to the beginning
                        mix_channel.sample_players[player].loops_remaining -= 1
                        mix_channel.sample_players[player].sample_pos = 0
                    elif mix_channel.sample_players[player].loops_remaining == 0:
                        # At the end and not looping, the sample has finished playing
                        mix_channel.sample_players[player].status = player_finished
                        break
                    else:
                        # Looping infinitely, loop back to the beginning
                        mix_channel.sample_players[player].sample_pos = 0

        # Check if the sound has finished
        if mix_channel.sample_players[player].status is player_finished:
            # Sound has finished, send notification and set player to idle status
            event_index = get_first_available_audio_event_on_mixer_channel(mix_channel)
            if event_index != -1:
                mix_channel.events[event_index].event = event_sound_stop
                mix_channel.events[event_index].channel = channel
                mix_channel.events[event_index].player = player
                mix_channel.events[event_index].sample_number = mix_channel.sample_players[player].sample_number

            # TODO: Log error if events are full

            # The sample play is now idle (ready to play another sample)
            mix_channel.sample_players[player].status = player_idle

    # Apply channel volume
    # TODO: implement me (this might be handled already by SDL_Mixer)

    # Apply channel envelopes (if applicable)
    apply_ducking_envelopes_to_mixer_channel_s16(stream, length, mix_channel)

    # Release the lock on the channel mutex
    SDL_UnlockMutex(mix_channel.mutex)

cdef void apply_ducking_envelopes_to_mixer_channel_s16(void *stream, int length, MixerChannel* mix_channel) nogil:
    """
    Applies any in-process ducking envelopes to the specified mixer channel output buffer
    :param stream:
    :param length:
    :param mix_channel:
    :return: void
    """
    if mix_channel == NULL:
        return

    # Attempt to lock the track/channel mutex while performing operations on the track/channel
    if SDL_LockMutex(mix_channel.mutex) != 0:
        return

    cdef DuckingEnvelope *envelope
    envelope = mix_channel.ducking_envelopes

    # Are there any envelopes to process?
    if envelope == NULL:
        # Release the lock on the channel mutex
        SDL_UnlockMutex(mix_channel.mutex)
        return

    cdef float sample_attenuation = 1.0

    # There is at least one ducking envelope to process, loop over output buffer samples
    for sample_index in range(length):

        sample_attenuation = 1.0

        # Loop over any envelopes to process for the channel
        while envelope != NULL:
            # TODO: process envelopes (use minimum value across all envelopes)

            # Get the next envelope (if there is one, they are stored in a linked list)
            envelope = envelope.next

        # Apply envelope attenuation
        if sample_attenuation < 1.0:
            # TODO: Calculate new volume and apply it
            # TODO: Turn get sample into an inline function (.pxd file)
            pass

    # Release the lock on the channel mutex
    SDL_UnlockMutex(mix_channel.mutex)


cdef class AudioOutput:
    """:class:`AudioOutput` class is the base for initializing the internal
    audio.
    
    .. warning::
    
        You can instantiate only one AudioOutput in a process. It must be
        instantiated before any others components of the library.
    """

    cdef dict samples
    cdef int next_sample_number
    cdef int audio_init
    cdef readonly int rate
    cdef readonly int channels
    cdef readonly int buffersize
    cdef readonly int encoding
    cdef int audio_format
    cdef int supported_formats
    cdef list mixer_channels
    cdef Mix_Chunk *raw_chunk_silence

    def __cinit__(self, *args, **kw):
        self.audio_init = 0
        self.raw_chunk_silence = NULL

    def __init__(self, rate=44100, channels=2, buffersize=1024, encoding=16,
                 formats=MIX_INIT_FLAC|MIX_INIT_MP3|MIX_INIT_OGG):
        self.samples = {}
        self.next_sample_number = 1
        self.rate = rate
        self.channels = channels
        self.buffersize = buffersize
        self.encoding = encoding
        self.audio_format = 0
        self.supported_formats = formats
        self.mixer_channels = []

        assert(encoding in (8, 16))
        assert(channels >= 1)
        assert(buffersize >= 0)

        if self._init_audio() < 0:
            raise AudioException('AudioOutput: unable to initialize audio')

        # Initialize the supported SDL_Mixer library formats with the requested formats
        self.supported_formats = Mix_Init(self.supported_formats)

        # Generate silence audio chunk/sample (used to play on each track since each track in SDL_Mixer
        # must play something to call its effects callback functions which are used in this library
        # to perform the actual sound generation/mixing)
        cdef uint8_t *silence = NULL
        cdef uint32_t length = self.rate * self.buffersize * self.channels
        silence = <uint8_t *>calloc(1, length)

        self.raw_chunk_silence = Mix_QuickLoad_RAW(silence, length)
        if self.raw_chunk_silence == NULL:
            raise AudioException('AudioOutput: unable to initialize and load silence')

    cdef int _init_audio(self):
        """
        Initializes the audio libraries. This function is considered private and should only
        be called from within this class.
        :return: int that indicates success (0) or failure (-1)
        """

        # Make sure we haven't already performed initialization
        if self.audio_init == 1:
            return 0

        # Initialize threading in the extension library and acquire the Python global interpreter lock
        PyEval_InitThreads()

        # Initialize the SDL audio system
        if SDL_Init(SDL_INIT_AUDIO) < 0:
            print('SDL_Init: %s' % SDL_GetError())
            return -1

        cdef unsigned int encoding = AUDIO_S8 if self.encoding == 8 else AUDIO_S16SYS
        self.audio_format = encoding

        # Initialize the SDL_Mixer library to establish the output audio format and encoding
        # (sample rate, bit depth, buffer size)
        if Mix_OpenAudio(self.rate, encoding, self.channels, self.buffersize):
            print('Mix_OpenAudio: %s' % SDL_GetError())
            return -1

        # Lock SDL from calling the audio callback functions
        SDL_LockAudio()

        # Determine the actual audio format in use by the opened audio device.  This may or may not match
        # the parameters used to initialize the output device.
        print('AudioOutput asked for ', self.rate, self.channels, self.buffersize)
        Mix_QuerySpec(&self.rate, NULL, &self.channels)
        print('AudioOutput received ', self.rate, self.channels, self.buffersize)

        # Unlock the SDL audio callback functions
        SDL_UnlockAudio()

        # Audio has now been initialized
        self.audio_init = 1
        return 0

    @property
    def supports_wav(self):
        return self.audio_init == 1

    @property
    def supports_ogg(self):
        return self.audio_init == 1 and (self.supported_formats & MIX_INIT_OGG) == MIX_INIT_OGG

    @property
    def supports_flac(self):
        return self.audio_init == 1 and (self.supported_formats & MIX_INIT_FLAC) == MIX_INIT_FLAC

    @property
    def supports_mp3(self):
        return self.audio_init == 1 and (self.supported_formats & MIX_INIT_MP3) == MIX_INIT_MP3

    def load_sample(self, str file_name, float default_volume=1.0, int simultaneous_limit=-1):
        """
        Loads a sample into memory from the specified file name. A pointer to the
        sample will be stored in a dictionary with the sample name as the key.
        :param file_name: The full file OS path to the sample file to load.
        :param default_volume: The default volume for this sample (0.0 to 1.0)
        :param simultaneous_limit: The maximum number of instances of this sound
        that may be played at one time (-1 means there is no limit)
        :return: The unique sample number for the newly loaded sample.  This number
        will be used to reference this particular sample from now on.  If
        the sample could not be loaded, 0 is returned.
        """

        # Check if sample file_name has already been loaded.  If so returns its
        # existing sample number
        for loaded_sample_num in self.samples:
            if file_name == self.samples[loaded_sample_num]['file_name']:
                return loaded_sample_num

        # String conversion from Python to char* (it takes a few steps)
        # See http://docs.cython.org/src/tutorial/strings.html for more information.
        # 1) convert the python string (str) to a byte string (use UTF-8 encoding)
        # 2) convert the python byte string to a C char* (can just do an assign)
        # 3) the C char* string is now ready for use in calls to the C library
        py_byte_file_name = file_name.encode('UTF-8')
        cdef char* c_file_name = py_byte_file_name
        py_byte_mode = "rb".encode('UTF-8')
        cdef char* c_mode = py_byte_mode

        # Load the sample file into memory
        cdef Mix_Chunk *chunk = Mix_LoadWAV_RW(SDL_RWFromFile(c_file_name, c_mode), 1)
        if chunk is NULL:
            print("An error occurred while loading sound file '{}': {}".format(file_name, SDL_GetError()))
            return 0

        # Ensure volume is in the range from 0.0 to 1.0
        default_volume = max(min(default_volume, 1.0), 0.0)

        # Compute the new volume setting (between 0 and MIX_MAX_VOLUME)
        chunk.volume = int(default_volume * MIX_MAX_VOLUME)

        # Store the chunk pointer in a python capsule (wraps a c pointer in a python object)
        # so it can be stored in a python dictionary
        sample_number = self.next_sample_number
        self.next_sample_number += 1
        self.samples[sample_number] = {}
        self.samples[sample_number]['file_name'] = file_name
        self.samples[sample_number]['chunk'] = pycapsule.PyCapsule_New(chunk, NULL, NULL)
        self.samples[sample_number]['limit'] = simultaneous_limit
        self.samples[sample_number]['instances'] = 0

        return sample_number

    def unload_sample(self, int sample_number):
        """
        Unloads a sample from memory and removes it from the dictionary of loaded sounds.
        :param sample_number: The sound/sample number (used as dictionary key)
        :return: True if the sample was successfully unloaded from memory and removed
        from the dictionary, False otherwise
        """
        cdef Mix_Chunk *chunk = NULL

        # Find the sample by name key in the dictionary
        if sample_number not in self.samples:
            return False

        # TODO: make sure sample is not currently playing (stop it first)

        # Sample was found, get the Mix_Chunk pointer from the capsule object and free it
        chunk = <Mix_Chunk*>pycapsule.PyCapsule_GetPointer(self.samples[sample_number]['chunk'], NULL)
        if chunk is not NULL:
            Mix_FreeChunk(chunk)

        # Finally remove the dictionary item
        del self.samples[sample_number]
        return True

    def play_sample_on_mixer_channel(self, int sample_number, int channel, float volume):
        """
        Plays the given sample on the specified mixer channel at the specified volume.
        :param sample_number:
        :param channel:
        :param volume: The volume to play
        :return:
        """

        # Find the sample by name key in the dictionary
        if sample_number not in self.samples:
            return False

        # If we have already reached the maximum number of instances currently playing,
        # do not allow this request to play another instance.
        # TODO: Add more options for what happens when instance limit is reached (replace oldest?)
        if self.samples[sample_number]['instances'] == self.samples[sample_number]['limit']:
            return False

        # Sample was found, get the Mix_Chunk pointer from the capsule object and free it
        sample = <Mix_Chunk*>pycapsule.PyCapsule_GetPointer(self.samples[sample_number]['chunk'], NULL)
        if sample is NULL:
            return False

        if channel < 0 or channel >= len(self.mixer_channels):
            return False

        cdef MixerChannel *mix_channel = \
            <MixerChannel*>pycapsule.PyCapsule_GetPointer(self.mixer_channels[channel], NULL)

        if mix_channel is NULL:
            return False

        if SDL_LockMutex(mix_channel.mutex) != 0:
            return False

        cdef int player = get_open_sample_player_on_mixer_channel(mix_channel)
        if player == -1:
            return False

        # Ensure volume is in the range from 0.0 to 1.0
        volume = max(min(volume, 1.0), 0.0)

        # Compute the new volume setting (between 0 and MIX_MAX_VOLUME)
        cdef int sample_volume = int(volume * MIX_MAX_VOLUME)

        mix_channel.sample_players[player].chunk = sample
        mix_channel.sample_players[player].status = player_pending
        mix_channel.sample_players[player].loops_remaining = 0
        mix_channel.sample_players[player].start_time = SDL_GetTicks()
        mix_channel.sample_players[player].volume = sample_volume
        mix_channel.sample_players[player].sample_pos = 0
        mix_channel.sample_players[player].sample_number = sample_number

        self.samples[sample_number]['instances'] += 1

        SDL_UnlockMutex(mix_channel.mutex)

        print("Playing sample #{} on channel {} player {}".format(sample_number, channel, player))

        return True

    def apply_ducking_envelope_to_mixer_channel(self, int channel, int delay_time, int attack_time,
                                                float attenuation, int release_point, int release_time):
        """
        Applies and executes a ducking envelope to the specified mixer channel.
        :param channel: The mixer channel to apply the envelope to.
        :param delay_time: The number of milliseconds to delay before the attack segment of the envelope starts.
        :param attack_time: The number of milliseconds for the attack (go from no attenuation to the
        full attenuation value).
        :param attenuation: The attenuation level to apply to the channel (0.0 = full attenuation to
        1.0 = no attenuation)
        :param release_point: The number of milliseconds from the start of the sound to begin the release
        segment of the envelope (NOTE: the user will be providing a time from the END of the sound, but
        this parameter requires the elapsed time from the beginning of the sound/envelope).
        :param release_time: The number of milliseconds for the release (go from full attenuation to no
        attenuation).  Once this time has elapsed, the envelope processing has finished.
        :return: None
        """

        # Retrieve the specified mixer channel
        if channel < 0 or channel >= len(self.mixer_channels):
            return False

        cdef MixerChannel *mix_channel = \
            <MixerChannel*>pycapsule.PyCapsule_GetPointer(self.mixer_channels[channel], NULL)

        if mix_channel is NULL:
            return False

        # Allocate a new ducking envelope struct
        cdef DuckingEnvelope *envelope = <DuckingEnvelope*>calloc(1, sizeof(DuckingEnvelope))
        if envelope == NULL:
            return False

        # Set the user-defined attributes
        envelope.delay_time = delay_time
        envelope.attack_time = attack_time
        envelope.attenuation = attenuation
        envelope.release_point = release_point
        envelope.release_time = release_time

        # Calculate/set the internal state attributes
        envelope.start_time = 0
        envelope.attack_start_samples = self.rate * delay_time // 1000
        envelope.release_start_samples = self.rate * release_point // 1000
        envelope.envelope_finished_samples = self.rate * (release_point + release_time) // 1000
        envelope.elapsed_samples = 0
        envelope.segment = pending_segment

        # Ensure the SDL audio callback functions are not called during this code (lock)
        SDL_LockAudio()

        # Insert the envelope into the beginning of the mixer channel's ducking envelope linked list
        if mix_channel.ducking_envelopes == NULL:
            mix_channel.ducking_envelopes = envelope
            envelope.next = NULL
        else:
            envelope.next = mix_channel.ducking_envelopes
            mix_channel.ducking_envelopes = envelope

        SDL_UnlockAudio()

        return True

    def add_mixer_channel(self, int simultaneous_sounds=1):
        """
        Adds a channel to the mixer.
        :param simultaneous_sounds: The maximum number of sounds that can be played simultaneously on the channel
        :return: The newly added channel number
        """
        cdef int channel = len(self.mixer_channels)

        # Create a new MixerChannel struct (C object) that will keep track of channel state/attributes
        mixer_channel = alloc_mixer_channel(channel, simultaneous_sounds)

        # Because the MixerChannel* returned cannot be converted to a Python object for storing in
        # a list, it is converted to a Python object using a capsule (wraps a C pointer in a
        # Python object).
        self.mixer_channels.append(pycapsule.PyCapsule_New(<void *>mixer_channel, NULL, NULL))

        # Setup callback function for mixer channel depending upon the audio format used
        cdef Mix_EffectFunc_t channel_callback_fn

        if self.audio_format == AUDIO_S8:
            channel_callback_fn = mix_track_callback_s8
        else:
            channel_callback_fn = mix_track_callback_s16sys

        with nogil:
            # Ensure the SDL audio callback functions are not called during this code (lock)
            SDL_LockAudio()

            # Set the number of channels to mix (will cause existing channels to be stopped and restarted if playing)
            # This is an SDL_Mixer library function call.
            Mix_AllocateChannels(channel + 1)

            # Register the channel/track callback function that will perform the actual mixing of sounds
            # on the channel/track.  Pass in the pointer to the mixer channel which will be passed to the
            # callback function.
            # This is an SDL_Mixer library function call.
            Mix_RegisterEffect(channel, channel_callback_fn, NULL, <void *>mixer_channel)

            # Allow the audio callback functions to be called (unlock)
            SDL_UnlockAudio()

        return channel


    def enable_mixer_channel(self, int channel):
        """
        Enables audio playback on the specified mixer channel (begins processing)
        :param channel:
        :return:
        """
        with nogil:
            Mix_PlayChannel(channel, self.raw_chunk_silence, -1)

    def enable_all_mixer_channels(self):
        """
        Enables audio playback on all mixer channels (begins processing)
        :return:
        """
        for channel in range(len(self.mixer_channels)):
            self.enable_mixer_channel(channel)

    def set_mixer_channel_volume(self, int channel, float volume):
        """
        Sets the volume of the specified mixer channel.
        :param channel: The mixer channel number
        :param volume: The new volume setting (between 0.0 and 1.0)
        :return:
        """
        if channel < 0 or channel >= len(self.mixer_channels):
            return False

        # Ensure volume is in the range from 0.0 to 1.0
        volume = max(min(volume, 1.0), 0.0)

        # Compute the new volume setting (between 0 and MIX_MAX_VOLUME)
        cdef int new_volume = int(volume * MIX_MAX_VOLUME)
        with nogil:
            Mix_Volume(channel, new_volume)

        return True

    def set_all_mixer_channel_volume(self, float volume):
        """
        Sets the volume of all mixer channels.
        :param volume: The new volume setting (between 0.0 and 1.0)
        :return:
        """
        cdef int channel = 0
        for channel in range(len(self.mixer_channels)):
            self.set_mixer_channel_volume(channel, volume)

    # TODO: Add process callbacks function designed to be called from MPF tick function

    def process_event_callbacks(self):
        """
        Designed to be called on every MPF tick, this function processes any state changes
        or events generated in the SDL callbacks (separate thread).
        """
        cdef MixerChannel *mix_channel

        # Loop over mixer channels, looking for any unprocessed events
        for channel in range(len(self.mixer_channels)):
            mix_channel = <MixerChannel*>pycapsule.PyCapsule_GetPointer(self.mixer_channels[channel], NULL)
            if mix_channel == NULL:
                continue

            # Lock the mixer channel so it can't be accessed in another thread
            SDL_LockMutex(mix_channel.mutex)

            for i in range(MAX_AUDIO_EVENTS):
                if mix_channel.events[i].event != event_none:
                    # TODO: implement event callbacks
                    pass

            # Unlock the mixer channel
            SDL_UnlockMutex(mix_channel.mutex)


def get_audio_output(**kwargs):
    """
    Function to initialize the PinAudio audio output
    :param kwargs:
    :return: AudioOutput
    """
    return AudioOutput(**kwargs)

def get_version():
    """
    Retrieves the current version of the PinAudio library
    :return: PinAudio version string
    """
    return __version__

def get_sdl_version():
    """
    Returns the version of the SDL library
    :return: SDL library version string
    """
    cdef SDL_version version
    SDL_GetVersion(&version)
    return 'SDL {}.{}.{}'.format(version.major, version.minor, version.patch)

def get_sdl_mixer_version():
    """
    Returns the version of the dynamically linked SDL_Mixer library
    :return: SDL_Mixer library version string
    """
    cdef SDL_version *version =  Mix_Linked_Version()
    return 'SDL_Mixer {}.{}.{}'.format(version.major, version.minor, version.patch)


ctypedef struct MixerChannel:
    # C structure that maintains mixer channel attributes and audio sample players
    # for playing samples/sounds on the channel.
    int channel
    int max_simultaneous_sounds
    int volume
    AudioSamplePlayer *sample_players
    DuckingEnvelope *ducking_envelopes
    SDL_mutex *mutex
    AudioEventData *events

cdef MixerChannel *alloc_mixer_channel(int channel, int simultaneous_sounds=1) nogil:
    """ Allocates memory and creates a new mixer channel.
    The memory allocated by this method must be freed using the free_mixer_channel
    method or a memory leak will occur.
    :param channel: The channel number for the new mixer channel.
    :param simultaneous_sounds: The maximum number of sounds that may be played
    simultaneously on this mixer channel.
    """

    # Allocate memory and assign it to the new mixer channel structure
    cdef MixerChannel *mix_channel = <MixerChannel *>calloc(1, sizeof(MixerChannel))

    # Set the mixer channel attributes
    mix_channel.channel = channel
    mix_channel.max_simultaneous_sounds = simultaneous_sounds

    # Create a mutex used for locking/thread protection in SDL
    mix_channel.mutex = SDL_CreateMutex()

    # Allocate memory for the audio sample player objects needed for the desired number of
    # simultaneous sounds that can be played on the channel.
    mix_channel.sample_players = <AudioSamplePlayer *>calloc(mix_channel.max_simultaneous_sounds, sizeof(AudioSamplePlayer))

    # Initialize mixer channel settings
    for i in range(mix_channel.max_simultaneous_sounds):
        mix_channel.sample_players[i].chunk = NULL
        mix_channel.sample_players[i].status = player_idle
        mix_channel.sample_players[i].loops_remaining = 0
        mix_channel.sample_players[i].start_time = 0
        mix_channel.sample_players[i].volume = 0
        mix_channel.sample_players[i].sample_pos = 0

    # Initialize ducking envelopes
    mix_channel.ducking_envelopes = NULL

    # Initialize audio events
    mix_channel.events = <AudioEventData*>calloc(MAX_AUDIO_EVENTS, sizeof(AudioEventData))
    for i in range(MAX_AUDIO_EVENTS):
        mix_channel.events[i].event = event_none
        mix_channel.events[i].channel = 0
        mix_channel.events[i].player = 0
        mix_channel.events[i].sample_number = 0

    # Return the new mixer channel object pointer
    return mix_channel

cdef void free_mixer_channel(MixerChannel* mix_channel) nogil:
    """ Frees memory allocated for the specified mixer channel.
    """

    if mix_channel == NULL:
        return

    SDL_DestroyMutex(mix_channel.mutex)

    # Free all audio sample players for the channel
    free(mix_channel.sample_players)

    # Free all ducking envelopes
    cdef DuckingEnvelope *envelope = mix_channel.ducking_envelopes
    cdef DuckingEnvelope *next_envelope = NULL
    while envelope != NULL:
        next_envelope = envelope.next
        free(envelope)
        envelope = next_envelope

    # Free audio event data
    free(mix_channel.events)

    # Free mixer channel itself
    free(mix_channel)

cdef int get_open_sample_player_on_mixer_channel(MixerChannel* mix_channel) nogil:
    """ Returns the index of the first free audio sample player on the specified
    mixer channel.  If all players are currently busy playing, -1 is returned.
    :param mix_channel: The mixer channel to check for open sample players.
    """
    for i in range(mix_channel.max_simultaneous_sounds):
        if mix_channel.sample_players[i].status == player_idle:
            return i

    return -1

cdef int get_first_available_audio_event_on_mixer_channel(MixerChannel* mix_channel) nogil:
    """
    Returns the index of the first available audio event on the specified mixer channel.
    If all audio events are currently in use, -1 is returned.
    :param mix_channel:
    :return: The index of the first available audio event.  -1 if all are in use.
    """
    for i in range(MAX_AUDIO_EVENTS):
        if mix_channel.events[i].event == event_none:
            return i

    return -1

cdef enum AudioSamplePlayerStatus:
    player_idle,
    player_pending,
    player_playing,
    player_finished

ctypedef struct AudioSamplePlayer:
    # The AudioSamplePlayer keeps track of the current sample position in the source audio
    # chunk and is also keeps track of variables for sound looping and determining when the
    # sound has finished playing.
    Mix_Chunk *chunk
    AudioSamplePlayerStatus status
    int loops_remaining
    uint32_t start_time
    int volume
    int sample_pos
    int sample_number

cdef enum DuckingEnvelopeSegment:
    pending_segment,
    delay_segment,
    attack_segment,
    attenuation_segment,
    release_segment,
    finished_segment

ctypedef struct DuckingEnvelope:
    # A DuckingEnvelope struct keeps the state of a single envelope used for audio
    # ducking a mixer channel.

    # The following attributes are set by the user
    int delay_time
    int attack_time
    float attenuation
    int release_point
    int release_time

    # The following attributes are used to keep track of the current envelope state
    uint32_t start_time
    uint32_t attack_start_samples
    uint32_t release_start_samples
    uint32_t envelope_finished_samples
    uint32_t elapsed_samples
    DuckingEnvelopeSegment segment

    # Ducking envelopes are used in a linked list.  This attribute points to the next
    # envelope in the list (may be NULL)
    DuckingEnvelope *next


ctypedef struct FadeEnvelope:
    int delay_time
    int fade_in_time
    int fade_out_point
    int fade_out_time

cdef enum AudioEvent:
    event_none,
    event_sound_start,
    event_sound_stop

ctypedef struct AudioEventData:
    AudioEvent event
    int channel
    int player
    int sample_number

cdef struct Sample16Bytes:
    int8_t byte1
    int8_t byte2

cdef union Sample16Bit:
    int16_t value
    Sample16Bytes bytes

