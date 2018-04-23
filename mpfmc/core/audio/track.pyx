#!python
#cython: embedsignature=True, language_level=3

from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
cimport cpython.pycapsule as pycapsule
import logging

from mpfmc.core.audio.sdl2 cimport *
from mpfmc.core.audio.gstreamer cimport *
from mpfmc.core.audio.inline cimport lerpU8, in_out_quad
from mpfmc.core.audio.notification_message cimport *
from mpfmc.core.audio.track cimport *


# Max and min 16-bit audio sample values (used in audio mixing functions)
DEF MAX_AUDIO_VALUE_S16 = ((1 << (16 - 1)) - 1)
DEF MIN_AUDIO_VALUE_S16 = -(1 << (16 - 1))


# ---------------------------------------------------------------------------
#    Track base class
# ---------------------------------------------------------------------------
cdef class Track:
    """
    Track base class
    """

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
        self._name = name
        self._number = track_num
        self._events_when_stopped = None
        self._events_when_played = None
        self._events_when_paused = None

        # Allocate memory for the track state (common among all track types)
        self.state = <TrackState*> PyMem_Malloc(sizeof(TrackState))
        self.state.mix_callback_function = NULL
        self.state.type_state = NULL
        self.state.number = track_num
        self.state.buffer = <Uint8 *>PyMem_Malloc(buffer_size)
        self.state.buffer_size = buffer_size
        self.state.ducking_control_points = g_array_sized_new(False, True, sizeof(guint8), CONTROL_POINTS_PER_BUFFER)
        self.log.debug("Allocated track audio buffer (%d bytes)", buffer_size)

        # The easiest way to pass a C pointer in a constructor is to wrap it in a PyCapsule
        # (see https://docs.python.org/3.4/c-api/capsule.html).  This basically wraps the
        # pointer in a Python object. It can be extracted using PyCapsule_GetPointer.
        self.state.callback_data = <AudioCallbackData*>pycapsule.PyCapsule_GetPointer(audio_callback_data, NULL)

        self.state.status = track_status_playing
        self.state.fade_steps = 0
        self.state.fade_steps_remaining = 0
        new_volume = <Uint8>min(max(volume * SDL_MIX_MAXVOLUME, 0), SDL_MIX_MAXVOLUME)
        self.state.volume = new_volume
        self.state.fade_volume_current = new_volume
        self.state.fade_volume_start = new_volume
        self.state.fade_volume_target = new_volume

        self.state.notification_messages = NULL

    def __dealloc__(self):
        """Destructor"""
        SDL_LockAudio()
        g_array_free(self.state.ducking_control_points, True)
        PyMem_Free(self.state)
        SDL_UnlockAudio()

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
    def type(self):
        raise NotImplementedError('Must be overridden in derived class')

    @property
    def number(self):
        """Return the track number"""
        cdef int number = -1
        if self.state != NULL:
            SDL_LockAudio()
            number = self.state.number
            SDL_UnlockAudio()
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
            SDL_LockAudio()
            fading = self.state.fade_steps_remaining > 0
            SDL_UnlockAudio()
        return fading

    def clear_context(self, context):
        """Stop all sounds played from the specified context."""
        raise NotImplementedError('Must be overridden in derived class')

    def set_volume(self, float volume, float fade_seconds = 0.0):
        """Sets the current track volume with an optional fade time"""
        cdef Uint8 new_volume = <Uint8>min(max(volume * SDL_MIX_MAXVOLUME, 0), SDL_MIX_MAXVOLUME)
        SDL_LockAudio()

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

        SDL_UnlockAudio()

    def play(self, float fade_in_seconds = 0.0):
        """
        Starts playing the track so it can begin processing sounds. Function has no effect if
        the track is already playing.
        Args:
            fade_in_seconds: The number of seconds to fade in the track
        """
        self.log.debug("play - Begin sound processing on track")

        SDL_LockAudio()

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
                    self.mc.post_mc_native_event(event, track=self._name)
        else:
            self.log.warning("play - Action may only be used when a track is stopped or is in the process "
                             "of stopping; action will be ignored.")

        SDL_UnlockAudio()

    def stop(self, float fade_out_seconds = 0.0):
        """
        Stops the track and clears out any playing sounds. Function has no effect if the track is
        already stopped.
        Args:
            fade_out_seconds: The number of seconds to fade out the track
        """
        self.log.debug("stop - Stop sound processing on track and clear state")

        SDL_LockAudio()

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

        SDL_UnlockAudio()

    def pause(self, float fade_out_seconds = 0.0):
        """
        Pauses the track. Sounds will continue from where they left off when the track is resumed.
        Function has no effect unless the track is playing.
        Args:
            fade_out_seconds: The number of seconds to fade out the track
        """
        self.log.debug("pause - Pause sound processing on track")

        SDL_LockAudio()

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

        SDL_UnlockAudio()

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
    #    Global C functions designed to be called from the static audio callback
    #    function (these functions do not use the GIL).
    #
    #    Note: Because these functions are only called from the audio callback
    #    function, we do not need to lock and unlock the mutex in these functions
    #    (locking/unlocking of the mutex is already performed in the audio
    #    callback function.
    # ---------------------------------------------------------------------------

    @staticmethod
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
                ducking_volume = g_array_index_uint8(track.ducking_control_points, control_point)
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

            Track.mix_audio(output_buffer + buffer_pos, track_buffer + buffer_pos, current_chunk_bytes, track_volume)

            output_buffer_bytes_remaining -= current_chunk_bytes
            buffer_pos += current_chunk_bytes
            control_point += 1

    @staticmethod
    cdef void mix_audio(Uint8* output_buffer, const Uint8* input_buffer, Uint32 buffer_length, int volume) nogil:
        """
        Mixes input buffer samples into existing output buffer samples applying the specified volume setting.
        
        Args:
            output_buffer: Output audio buffer
            input_buffer: Input audio buffer
            buffer_length: Length of audio buffers to process (input and output)
            volume: Volume level to apply to input buffer samples 

        """
        cdef Sample16 input_sample, output_sample
        cdef int temp_sample
        cdef Uint32 buffer_pos = 0

        while buffer_pos < buffer_length:

            # Get sample (2 bytes) from the input buffer and combine into 16-bit value
            input_sample.bytes.byte0 = input_buffer[buffer_pos]
            input_sample.bytes.byte1 = input_buffer[buffer_pos + 1]

            # Get sample (2 bytes) from the output buffer and combine into 16-bit value
            output_sample.bytes.byte0 = output_buffer[buffer_pos]
            output_sample.bytes.byte1 = output_buffer[buffer_pos + 1]

            # Calculate the new output sample (mix the input sample multiplied by the volume with the existing output
            # sample). The temporary output sample is a 32-bit value to avoid overflow.
            temp_sample = output_sample.value + ((input_sample.value * volume) // SDL_MIX_MAXVOLUME)

            # Clip the temp sample back to a 16-bit value (will cause distortion if samples
            # on channel are outside of the allowable 16-bit int range)
            if temp_sample > MAX_AUDIO_VALUE_S16:
                temp_sample = MAX_AUDIO_VALUE_S16
            elif temp_sample < MIN_AUDIO_VALUE_S16:
                temp_sample = MIN_AUDIO_VALUE_S16

            # Write the new output sample back to the output buffer (from
            # a 32-bit value back to a 16-bit value that we know is in 16-bit value range)
            output_sample.value = temp_sample
            output_buffer[buffer_pos] = output_sample.bytes.byte0
            output_buffer[buffer_pos + 1] = output_sample.bytes.byte1

            buffer_pos += 2

    @staticmethod
    cdef void mix_audio_stereo(Uint8* output_buffer, const Uint8* input_buffer, Uint32 buffer_length,
                               int volume_left, int volume_right) nogil:
        """
        Mixes input buffer samples into existing output buffer samples applying the specified volume setting
        to the left and right channels.
        
        Args:
            output_buffer: Output audio buffer
            input_buffer: Input audio buffer
            buffer_length: Length of audio buffers to process (input and output)
            volume_left: Volume level to apply to the input buffer left channel samples 
            volume_right: Volume level to apply to the input buffer right channel samples
            
        Notes:
            SDL audio buffers are in interleaved format with the left channel first in stereo buffers.

        """
        cdef Sample16 input_sample, output_sample
        cdef int temp_sample
        cdef Uint32 buffer_pos = 0

        while buffer_pos < buffer_length:

            # Process left channel

            # Get sample (2 bytes) from the input buffer and combine into 16-bit value
            input_sample.bytes.byte0 = input_buffer[buffer_pos]
            input_sample.bytes.byte1 = input_buffer[buffer_pos + 1]

            # Get sample (2 bytes) from the output buffer and combine into 16-bit value
            output_sample.bytes.byte0 = output_buffer[buffer_pos]
            output_sample.bytes.byte1 = output_buffer[buffer_pos + 1]

            # Calculate the new output sample (mix the input sample multiplied by the volume with the existing output
            # sample). The temporary output sample is a 32-bit value to avoid overflow.
            temp_sample = output_sample.value + ((input_sample.value * volume_left) // SDL_MIX_MAXVOLUME)

            # Clip the temp sample back to a 16-bit value (will cause distortion if samples
            # on channel are outside of the allowable 16-bit int range)
            if temp_sample > MAX_AUDIO_VALUE_S16:
                temp_sample = MAX_AUDIO_VALUE_S16
            elif temp_sample < MIN_AUDIO_VALUE_S16:
                temp_sample = MIN_AUDIO_VALUE_S16

            # Write the new output sample back to the output buffer (from
            # a 32-bit value back to a 16-bit value that we know is in 16-bit value range)
            output_sample.value = temp_sample
            output_buffer[buffer_pos] = output_sample.bytes.byte0
            output_buffer[buffer_pos + 1] = output_sample.bytes.byte1

            buffer_pos += 2

            # Process right channel

            # Get sample (2 bytes) from the input buffer and combine into 16-bit value
            input_sample.bytes.byte0 = input_buffer[buffer_pos]
            input_sample.bytes.byte1 = input_buffer[buffer_pos + 1]

            # Get sample (2 bytes) from the output buffer and combine into 16-bit value
            output_sample.bytes.byte0 = output_buffer[buffer_pos]
            output_sample.bytes.byte1 = output_buffer[buffer_pos + 1]

            # Calculate the new output sample (mix the input sample multiplied by the volume with the existing output
            # sample). The temporary output sample is a 32-bit value to avoid overflow.
            temp_sample = output_sample.value + ((input_sample.value * volume_right) // SDL_MIX_MAXVOLUME)

            # Clip the temp sample back to a 16-bit value (will cause distortion if samples
            # on channel are outside of the allowable 16-bit int range)
            if temp_sample > MAX_AUDIO_VALUE_S16:
                temp_sample = MAX_AUDIO_VALUE_S16
            elif temp_sample < MIN_AUDIO_VALUE_S16:
                temp_sample = MIN_AUDIO_VALUE_S16

            # Write the new output sample back to the output buffer (from
            # a 32-bit value back to a 16-bit value that we know is in 16-bit value range)
            output_sample.value = temp_sample
            output_buffer[buffer_pos] = output_sample.bytes.byte0
            output_buffer[buffer_pos + 1] = output_sample.bytes.byte1

            buffer_pos += 2

    @staticmethod
    cdef void apply_volume(Uint8* output_buffer, const Uint8* input_buffer, Uint32 buffer_length, int volume) nogil:
        """
        Applies a volume level to the input buffer samples and copies them to the output buffer.
        Args:
            output_buffer: Output audio buffer
            input_buffer: Input audio buffer
            buffer_length: Length of audio buffers to process (input and output)
            volume: Volume level to apply to input buffer samples 

        """
        cdef Sint16* output_samples = <Sint16*>output_buffer
        cdef Sint16* input_samples = <Sint16*>input_buffer
        cdef Uint32 buffer_pos = 0

        # We will be iterating over the audio buffers two bytes at a time (16-bit sample values) so
        # effectively the buffer is half the length since we are casting the buffer pointer to 16-bit
        buffer_length = buffer_length // 2

        while buffer_pos < buffer_length:
            output_samples[buffer_pos] = (input_samples[buffer_pos] * volume) // SDL_MIX_MAXVOLUME
            buffer_pos += 1

    @staticmethod
    cdef void apply_volume_stereo(Uint8* output_buffer, const Uint8* input_buffer, Uint32 buffer_length,
                                  int volume_left, int volume_right) nogil:
        """
        Applies a volume level to the left and right channel of the input buffer samples and copies them 
        to the output buffer.
        
        Args:
            output_buffer: Output audio buffer
            input_buffer: Input audio buffer
            buffer_length: Length of audio buffers to process (input and output)
            volume_left: Volume level to apply to input buffer left channel samples 
            volume_right: Volume level to apply to input buffer right channel samples

        Notes:
            SDL audio buffers are in interleaved format with the left channel first in stereo buffers.

        """
        cdef Sint16* output_samples = <Sint16*>output_buffer
        cdef Sint16* input_samples = <Sint16*>input_buffer
        cdef Uint32 buffer_pos = 0

        # We will be iterating over the audio buffers two bytes at a time (16-bit sample values) so
        # effectively the buffer is half the length since we are casting the buffer pointer to 16-bit
        buffer_length = buffer_length // 2

        while buffer_pos < buffer_length:
            output_samples[buffer_pos] = (input_samples[buffer_pos] * volume_left) // SDL_MIX_MAXVOLUME
            buffer_pos += 1

            output_samples[buffer_pos] = (input_samples[buffer_pos] * volume_right) // SDL_MIX_MAXVOLUME
            buffer_pos += 1
