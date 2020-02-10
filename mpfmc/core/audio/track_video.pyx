#!python
#cython: embedsignature=True, language_level=3

from libc.stdio cimport FILE, fopen, fprintf, sprintf, fflush, fclose
from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
import cython
import logging
from math import ceil

from mpfmc.core.audio.sdl2 cimport *
from mpfmc.core.audio.gstreamer cimport *
from mpfmc.core.audio.track cimport *
from mpfmc.core.audio.inline cimport in_out_quad
from mpfmc.core.audio.notification_message cimport *
from mpfmc.core.audio.audio_exception import AudioException
from mpfmc.core.video.gst_video import GstVideo
from mpfmc.assets.sound import DuckingSettings
from mpfmc.core.audio.track_video cimport *


# ---------------------------------------------------------------------------
#    TrackVideo class
# ---------------------------------------------------------------------------
cdef class TrackVideo(Track):
    """
    Video track class (used to route audio signals from videos into the audio system)
    """

    def __init__(self, object mc, object audio_callback_data, str name, int track_num, int buffer_size,
                 float volume=1.0):
        """
        Constructor
        Args:
            mc: The media controller app
            audio_callback_data: The AudioCallbackData struct wrapped in a PyCapsule
            name: The track name
            track_num: The track number
            buffer_size: The length of the track audio buffer in bytes
            volume: The track volume (0.0 to 1.0)
        """
        # IMPORTANT: Call super class init function to allocate track state memory!
        super().__init__(mc, audio_callback_data, name, track_num, buffer_size, volume)

        self.log = logging.getLogger("Track." + str(track_num) + ".TrackVideo." + name)

        # Dictionary of GstVideo class objects keyed by video asset name
        self._active_videos_by_name = dict()

        SDL_LockAudio()

        # Set track type specific settings
        self.state.mix_callback_function = TrackVideo.mix_playing_sounds

        # Allocate memory for the specific track type state struct (TrackSoundLoopState)
        self.type_state = <TrackVideoState*> PyMem_Malloc(sizeof(TrackVideoState))
        self.state.type_state = <void*>self.type_state

        # TODO: Initialize track specific state structures

        self.log.debug("Created Track %d %s", self.number, self.name)

        SDL_UnlockAudio()

    def __dealloc__(self):
        """Destructor"""

        SDL_LockAudio()

        # Free the specific track type state and other allocated memory
        if self.type_state != NULL:

            if self.type_state.videos != NULL:
                iterator = self.type_state.videos
                while iterator != NULL:
                    g_slice_free1(sizeof(VideoSettings), iterator.data)
                    iterator = iterator.next

                g_slist_free(self.type_state.videos)
                self.type_state.videos = NULL

            PyMem_Free(self.type_state)
            self.type_state = NULL
            if self.state != NULL:
                self.state.type_state = NULL

        SDL_UnlockAudio()

    def __repr__(self):
        return '<Track.{}.Video.{}>'.format(self.number, self.name)

    @property
    def type(self):
        return "video"

    @property
    def supports_in_memory_sounds(self):
        """Return whether or not track accepts in-memory sounds"""
        return False

    @property
    def supports_streaming_sounds(self):
        """Return whether or not track accepts streaming sounds"""
        return True

    def clear_context(self, context):
        """Stop all sounds played from the specified context."""
        pass

    def stop_all_sounds(self, float fade_out_seconds = 0.0):
        """
        Stops all playing sounds immediately on the track.
        Args:
            fade_out_seconds: The number of seconds to fade out the sounds before stopping
        """
        pass

    def process(self):
        """Processes track messages each tick."""

        # Lock the mutex to ensure no audio data is changed during the playback processing
        # (multi-threaded protection)
        SDL_LockAudio()

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
        SDL_UnlockAudio()

    cdef process_notification_message(self, NotificationMessageContainer *notification_message):
        """Process a notification message to this track"""

        if notification_message == NULL:
            return

        SDL_LockAudio()

        # Check for track notification messages first (they do not need sound instance information)
        # TODO: Determine how to handle track notifications (video track should not be allowed to stop/pause)

        # TODO: Process track-specific notification messages

        SDL_UnlockAudio()

    def connect_video(self, str name not None, object video_obj, object ducking=None):
        cdef VideoSettings *video
        cdef GstVideo *gst_video_ptr = <GstVideo*>cython.address(video_obj.video)

        # Create new video
        video = <VideoSettings*>g_slice_alloc0(sizeof(VideoSettings))
        video.stream = <SampleStream*>PyMem_Malloc(sizeof(SampleStream))

        # Video stream
        video.stream.pipeline = gst_video.pipeline
        video.stream.sink = gst_video.appsink_audio
        video.stream.buffer = NULL
        video.stream.sample = NULL
        video.stream.map_buffer_pos = 0
        video.stream.map_contains_valid_sample_data = 0
        video.stream.null_buffer_count = 0

        # Video settings
        video.volume = SDL_MIX_MAXVOLUME
        video.sample_pos = 0
        video.fading_status = fading_status_not_fading
        video.fade_in_steps = 0
        video.fade_out_steps = 0
        video.fade_steps_remaining = 0
        video.marker_count = 0
        video.markers = NULL
        video.about_to_finish_marker = no_marker

        # Ducking settings
        if ducking and ducking.track_bit_mask != 0:
            # To convert between the number of seconds and a buffer position (bytes), we need to
            # account for the sample rate (samples per second), the number of audio channels, and the
            # number of bytes per sample (all samples are 16 bits)
            video.video_has_ducking = True
            video.ducking_stage = ducking_stage_delay
            video.ducking_settings.track_bit_mask = ducking.track_bit_mask
            video.ducking_settings.attack_start_pos = ducking.delay * self.state.callback_data.seconds_to_bytes_factor
            video.ducking_settings.attack_duration = ducking.attack * self.state.callback_data.seconds_to_bytes_factor
            video.ducking_settings.attenuation_volume = <Uint8>(ducking.attenuation * SDL_MIX_MAXVOLUME)
            video.ducking_settings.release_duration = ducking.release * self.state.callback_data.seconds_to_bytes_factor

            # Release point is relative to the end of the sound
            video.ducking_settings.release_start_pos = (gst_video.get_duration() - video.ducking.release_point) * \
                                                       self.state.callback_data.seconds_to_bytes_factor
        else:
            # Video does not have ducking, assign settings appropriately
            video.sound_has_ducking = False
            video.ducking_stage = ducking_stage_idle
            video.ducking_settings.track_bit_mask = 0
            video.ducking_settings.attack_start_pos = 0
            video.ducking_settings.attack_duration = 0
            video.ducking_settings.attenuation_volume = SDL_MIX_MAXVOLUME
            video.ducking_settings.release_duration = 0
            video.ducking_settings.release_start_pos = 0

        SDL_LockAudio()

        # Add new video to the video list
        self.type_state.videos = g_slist_prepend(self.type_state.videos, video)
        self._active_videos_by_name[name] = video

        SDL_UnlockAudio()

    def disconnect_video(self, str name not None):
        # TODO: remove video so it won't be processed anymore

        del self._active_videos_by_name[name]


    # ---------------------------------------------------------------------------
    #    Static C functions designed to be called from the static audio callback
    #    function (these functions do not use the GIL).
    #
    #    Note: Because these functions are only called from the audio callback
    #    function, we do not need to lock and unlock the mutex in these functions
    #    (locking/unlocking of the mutex is already performed in the audio
    #    callback function.
    # ---------------------------------------------------------------------------

    @staticmethod
    cdef void mix_playing_sounds(TrackState *track, Uint32 buffer_length, AudioCallbackData *callback_data) nogil:
        """
        Mixes any sounds that are playing on the specified standard track into the specified audio buffer.
        Args:
            track: A pointer to the TrackState data structure for the track
            buffer_length: The length of the output buffer (in bytes)
            callback_data: The audio callback data structure
        Notes:
            Notification messages are generated.
        """
        cdef TrackState *target_track
        cdef TrackVideoState *video_track

        if track == NULL or track.type_state == NULL:
            return

        video_track = <TrackVideoState*>track.type_state

        # TODO: Implement low-level audio mixing code

cdef bint get_streaming_sound_samples(SoundSettings *sound, Uint32 length, Uint8 *output_buffer, int channels,
                                      Uint8 volume, TrackState *track, int player_num) nogil:
    """
    Retrieves the specified number of bytes from the source sound streaming buffer and mixes them
    into the track output buffer at the specified volume.

    Args:
        sound: A pointer to a SoundSettings struct (contains all sound state and settings to play the sound)
        length: The number of samples to retrieve and place in the output buffer
        output_buffer: The output buffer
        channels: The number of channels in the output buffer (1 = mono, 2 = stereo)
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
                if channels == 2 and False:
                    # disabled for now
                    Track.mix_audio_stereo(output_buffer + buffer_pos,
                                           sound.sample.data.stream.map_info.data + sound.sample.data.stream.map_buffer_pos,
                                           samples_remaining_to_output,
                                           sound.volume_left,
                                           sound.volume_right)
                else:
                    SDL_MixAudioFormat(output_buffer + buffer_pos,
                                       sound.sample.data.stream.map_info.data + sound.sample.data.stream.map_buffer_pos,
                                       track.callback_data.format, samples_remaining_to_output, volume)

                # Update buffer position pointers
                sound.sample.data.stream.map_buffer_pos += samples_remaining_to_output
                sound.sample_pos += samples_remaining_to_output

                # Sound is not finished, but the output buffer has been filled
                return False
            else:
                # Entire buffer of leftover samples consumed.  Free the buffer resources to prepare for next call
                if channels == 2 and False:
                    # disabled for now
                    Track.mix_audio_stereo(output_buffer + buffer_pos,
                                           sound.sample.data.stream.map_info.data + sound.sample.data.stream.map_buffer_pos,
                                           samples_remaining_to_output,
                                           sound.volume_left,
                                           sound.volume_right)
                else:
                    SDL_MixAudioFormat(output_buffer + buffer_pos,
                                       sound.sample.data.stream.map_info.data + sound.sample.data.stream.map_buffer_pos,
                                       track.callback_data.format, samples_remaining_in_map, volume)

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

cdef inline VideoSettings *_create_video_settings() nogil:
    """
    Creates a new video settings struct.
    :return: A pointer to the new settings struct.
    """
    return <VideoSettings*>g_slice_alloc0(sizeof(VideoSettings))
