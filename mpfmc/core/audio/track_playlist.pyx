#!python
#cython: embedsignature=True, language_level=3

from libc.stdio cimport FILE, fopen, fprintf, sprintf, fflush, fclose
from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
cimport cpython.pycapsule as pycapsule
import cython
import logging

from mpfmc.config_collections.playlist import PlaylistInstance
from mpfmc.assets.sound import SoundInstance
from mpfmc.core.audio.sdl2 cimport *
from mpfmc.core.audio.gstreamer cimport *
from mpfmc.core.audio.track cimport *
from mpfmc.core.audio.inline cimport in_out_quad
from mpfmc.core.audio.track_standard cimport *
from mpfmc.core.audio.notification_message cimport *
from mpfmc.core.audio.track_playlist cimport *
from mpfmc.core.audio.audio_exception import AudioException


# ---------------------------------------------------------------------------
#    Settings
# ---------------------------------------------------------------------------

# The maximum number of consecutive null buffers to receive while streaming before
# terminating the sound (will cause drop outs)
DEF CONSECUTIVE_NULL_STREAMING_BUFFER_LIMIT = 2


# ---------------------------------------------------------------------------
#    TrackPlaylist class
# ---------------------------------------------------------------------------
cdef class TrackPlaylist(Track):
    """
    Playlist track class
    """

    def __init__(self, object mc, object audio_callback_data, str name, int track_num, int buffer_size,
                 float crossfade_time=0.0,
                 float volume=1.0):
        """
        Constructor
        Args:
            mc: The media controller app
            audio_callback_data: The AudioCallbackData struct wrapped in a PyCapsule
            name: The track name
            track_num: The track number
            buffer_size: The length of the track audio buffer in bytes
            crossfade_time: The default crossfade time (in seconds) for the track
            volume: The track volume (0.0 to 1.0)
        """
        # IMPORTANT: Call super class init function to allocate track state memory!
        super().__init__(mc, audio_callback_data, name, track_num, buffer_size, volume)

        self.log = logging.getLogger("Track." + str(track_num) + ".TrackPlaylist." + name)

        SDL_LockAudio()

        # Dictionary of SoundInstance class objects keyed by SoundInstance.id
        self._playing_sound_instances_by_id = dict()
        self._playlist_instances_by_sound_instance_id = dict()

        # Keep track of current and previous playlist
        self._current_playlist = None
        self._current_playlist_ending = False
        self._previous_playlist = None

        # Set track type specific settings
        self.state.mix_callback_function = TrackPlaylist.mix_playing_sounds

        # Allocate memory for the specific track type state struct (TrackPlaylistState)
        self.type_state = <TrackPlaylistState*> PyMem_Malloc(sizeof(TrackPlaylistState))
        self.state.type_state = <void*>self.type_state
        self.type_state.crossfade_time = crossfade_time

        # Hard-code the number of sound players to 3 (usually only need 2, except in the rare case
        # where a new playlist or song is crossfaded to when a crossfade is already in progress).
        self.type_state.sound_player_count = 3

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
            self.type_state.sound_players[i].current.ducking_control_points = g_array_sized_new(False, False, sizeof(guint8), CONTROL_POINTS_PER_BUFFER)
            self.type_state.sound_players[i].current.marker_count = 0
            self.type_state.sound_players[i].current.markers = g_array_new(False, False, sizeof(guint))
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
            self.type_state.sound_players[i].next.ducking_control_points = g_array_sized_new(False, False, sizeof(guint8), CONTROL_POINTS_PER_BUFFER)
            self.type_state.sound_players[i].next.marker_count = 0
            self.type_state.sound_players[i].next.markers = g_array_new(False, False, sizeof(guint))

        self.log.debug("Created Track %d %s with the following settings: "
                       "crossfade_time = %f, volume = %f",
                       self.number, self.name, self.type_state.crossfade_time, self.volume)

        SDL_UnlockAudio()

    def __dealloc__(self):
        """Destructor"""

        SDL_LockAudio()

        # Free the specific track type state and other allocated memory
        if self.type_state != NULL:
            for i in range(self.type_state.sound_player_count):
                g_array_free(self.type_state.sound_players[i].current.ducking_control_points, True)
                g_array_free(self.type_state.sound_players[i].next.ducking_control_points, True)
                g_array_free(self.type_state.sound_players[i].current.markers, True)
                g_array_free(self.type_state.sound_players[i].next.markers, True)

            PyMem_Free(self.type_state.sound_players)
            PyMem_Free(self.type_state)
            self.type_state = NULL
            if self.state != NULL:
                self.state.type_state = NULL

        SDL_UnlockAudio()

    def __repr__(self):
        return '<Track.{}.Playlist.{}>'.format(self.number, self.name)

    @property
    def type(self):
        return "playlist"

    @property
    def supports_in_memory_sounds(self):
        """Return whether or not track accepts in-memory sounds"""
        return True

    @property
    def supports_streaming_sounds(self):
        """Return whether or not track accepts streaming sounds"""
        return True

    cdef int _get_idle_sound_player(self):
        """
        Returns the index of the first idle sound player on the track.  If all
        players are currently busy playing, -1 is returned.
        """
        SDL_LockAudio()

        for index in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[index].status == player_idle:
                SDL_UnlockAudio()
                return index

        SDL_UnlockAudio()
        return -1

    def _reset_state(self):
        """Resets the track state (stops all playing sounds immediately)"""
        SDL_LockAudio()

        self.log.debug("Resetting track state (sounds will be stopped")

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle:
                # Set stop sound event
                send_sound_stopped_notification(i,
                                                self.type_state.sound_players[i].current.sound_id,
                                                self.type_state.sound_players[i].current.sound_instance_id,
                                                self.state)
                self.type_state.sound_players[i].status = player_idle

        SDL_UnlockAudio()

    def stop_all_sounds(self, float fade_out_seconds = 0.0):
        """
        Stops all playing sounds immediately on the track.
        Args:
            fade_out_seconds: The number of seconds to fade out the sounds before stopping
        """
        SDL_LockAudio()

        self.log.debug("Stopping all sounds")

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

        SDL_UnlockAudio()

    def process(self):
        """Processes the track queue each tick."""

        cdef GSList *iterator = NULL

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

            SDL_UnlockAudio()
            return

        self.log.debug("Processing notification message %d for sound instance (id: %d)",
                       notification_message.message, notification_message.sound_instance_id)

        if notification_message.sound_instance_id not in self._playing_sound_instances_by_id:
            self.log.warning("Received a notification message for a sound instance (id: %d) "
                             "that is no longer managed in the audio library. "
                             "Notification will be discarded.",
                             notification_message.sound_instance_id)

        elif notification_message.message == notification_sound_started:
            sound_instance = self._playing_sound_instances_by_id[notification_message.sound_instance_id]
            if sound_instance is not None:
                sound_instance.set_playing()

        elif notification_message.message == notification_sound_stopped:
            sound_instance = self._playing_sound_instances_by_id[notification_message.sound_instance_id]
            if sound_instance is not None:
                sound_instance.set_stopped()
                self.log.debug("Removing sound instance %s from playing sound "
                               "instance dictionary", str(sound_instance))
                del self._playing_sound_instances_by_id[sound_instance.id]

        elif notification_message.message == notification_sound_looping:
            sound_instance = self._playing_sound_instances_by_id[notification_message.sound_instance_id]
            if sound_instance is not None:
                sound_instance.set_looping()

        elif notification_message.message == notification_sound_about_to_finish:
            sound_instance = self._playing_sound_instances_by_id[notification_message.sound_instance_id]
            if sound_instance is not None:
                playlist = self._playlist_instances_by_sound_instance_id[notification_message.sound_instance_id]
                if playlist == self._current_playlist:
                    self.advance_playlist()

        elif notification_message.message == notification_sound_marker:
            sound_instance = self._playing_sound_instances_by_id[notification_message.sound_instance_id]
            if sound_instance is not None:
                sound_instance.set_marker(notification_message.data.marker.id)
        else:
            raise AudioException("Unknown notification message received on %s track", self.name)

        SDL_UnlockAudio()

    def play_playlist(self, dict playlist not None, str context=None, dict player_settings=None):
        """
        Immediately play a playlist.

        Args:
            playlist: The playlist asset object to play.
            context: The calling context (if any)
            player_settings: Settings to use for playback
        """

        self.log.debug("play_playlist - Preparing playlist '%s' for playback.", playlist)

        if player_settings is None:
            player_settings = dict()

        # Determine settings (override playlist with player settings)
        playlist_instance = PlaylistInstance(playlist, self.type_state.crossfade_time, context, player_settings)

        # Is there already a playlist playing?
        if self._current_playlist:
            # Already a playlist playing

            # Is there already a previous playlist that is still active (fading)?
            if self._previous_playlist:
                # TODO: need mechanism to delay new playlist until previous is finished
                # Set a callback function on previous playlist completion?
                pass

            # Get idle sound player
            sound_player = self._get_idle_sound_player()

            # If no idle sound player, queue the play request
            pass
        else:
            # No playlist playing
            self._current_playlist = playlist_instance

            # Get idle sound player
            sound_player = self._get_idle_sound_player()

            # Get next sound to play from playlist
            sound_name = self._current_playlist.get_next_sound_name()

            # Create sound instance
            sound = self.mc.sounds[sound_name]
            sound_instance = SoundInstance(sound,
                                           context,
                                           {
                                               'fade_in': 0.0,
                                               'fade_out': self._current_playlist.crossfade_time
                                           })

            # Assign sound instance to idle sound player
            # Save sound instance to active sound list

        pass

    def stop_playlist(self):
        """Immediately stop the currently playing playlist. Will fade out using the crossfade setting."""
        pass

    def advance_playlist(self):
        """Advance the currently playing playlist to the next sound."""

        # If no playlist is playing, do nothing
        if not self._current_playlist:
            return

        # Determine if playlist will now repeat/loop.  Post playlist looping events (if necessary)
        if self._current_playlist.end_of_playlist:
            if self._current_playlist.repeat and self._current_playlist.events_when_looping:
                    for event in self._current_playlist.events_when_looping:
                        self.mc.post_mc_native_event(event)

        # Set the next sound in the sound player and calculate the fades based on the crossfade setting
        next_sound_name = self._current_playlist.get_next_sound_name()
        if next_sound_name:
            pass
        else:
            self._current_playlist_ending = True

    def repeat_playlist(self, bint repeat=True):
        """Sets whether or not the currently playing playlist should repeat when finished."""
        pass

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

        SDL_LockAudio()

        # The sound cannot be played if the track is stopped or paused
        if self.state.status == track_status_stopped or self.state.status == track_status_paused:
            self.log.debug("_play_sound_on_sound_player - %s track is not currently playing and "
                           "therefore the request to play sound %s will be canceled",
                           self.name, sound_instance.name)
            sound_instance.set_canceled()
            SDL_UnlockAudio()
            return False

        if not sound_instance.sound.loaded:
            self.log.debug("Specified sound is not loaded, could not "
                           "play sound %s", sound_instance.name)
            SDL_UnlockAudio()
            return False

        # Make sure the player in range
        if player in range(self.type_state.sound_player_count):

            # If the specified sound player is not idle do not play the sound if force is not set
            if self.type_state.sound_players[player].status != player_idle and not force:
                self.log.debug("All sound players are currently in use, "
                               "could not play sound %s", sound_instance.name)
                SDL_UnlockAudio()
                return False

            # Add sound to the dictionary of active sound instances
            self.log.debug("Adding sound instance %s to active sound dictionary", str(sound_instance))
            self._playing_sound_instances_by_id[sound_instance.id] = sound_instance
            self._playlist_instances_by_sound_instance_id[sound_instance.id] = self._current_playlist

            # Check if sound player is idle
            if self.type_state.sound_players[player].status == player_idle:
                # Start the player playing the sound instance
                self._set_player_playing(cython.address(self.type_state.sound_players[player]), sound_instance)
            else:
                # The player is currently busy playing another sound, force it to be replaced with the sound instance
                self._set_player_replacing(cython.address(self.type_state.sound_players[player]), sound_instance)

            self.log.debug("Sound %s is set to begin playback on playlist track",
                           sound_instance.name)

            SDL_UnlockAudio()
            return True

        SDL_UnlockAudio()
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
        sound_settings.sound_id = sound_instance.sound_id
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
        g_array_set_size(sound_settings.markers, sound_settings.marker_count)
        for index in range(sound_instance.marker_count):
            g_array_insert_val_uint(sound_settings.markers,
                                    index,
                                    <guint>(sound_instance.markers[index]['time'] * self.state.callback_data.seconds_to_bytes_factor))

        # Set almost finished marker (calculate based on the end of the sound)
        sound_settings.almost_finished_marker = (sound_container.duration - sound_instance.almost_finished_time) * self.state.callback_data.seconds_to_bytes_factor

        # If the sound has ducking settings, apply them
        if sound_instance.ducking is not None and sound_instance.ducking.track_bit_mask != 0:
            # To convert between the number of seconds and a buffer position (bytes), we need to
            # account for the sample rate (samples per second), the number of audio channels, and the
            # number of bytes per sample (all samples are 16 bits)
            sound_settings.sound_has_ducking = True
            sound_settings.ducking_stage = ducking_stage_delay
            sound_settings.ducking_settings.track_bit_mask = sound_instance.ducking.track_bit_mask
            sound_settings.ducking_settings.attack_start_pos = sound_instance.ducking.delay * self.state.callback_data.seconds_to_bytes_factor
            sound_settings.ducking_settings.attack_duration = sound_instance.ducking.attack * self.state.callback_data.seconds_to_bytes_factor
            sound_settings.ducking_settings.attenuation_volume = <Uint8>(sound_instance.ducking.attenuation * SDL_MIX_MAXVOLUME)
            sound_settings.ducking_settings.release_duration = sound_instance.ducking.release * self.state.callback_data.seconds_to_bytes_factor

            # Release point is relative to the end of the sound
            sound_settings.ducking_settings.release_start_pos = (sound_container.duration - sound_instance.ducking.release_point) * self.state.callback_data.seconds_to_bytes_factor
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
        SDL_LockAudio()

        for i in range(self.type_state.sound_player_count):
            if self.type_state.sound_players[i].status != player_idle and \
                            self.type_state.sound_players[i].current.sound_instance_id == sound_instance.id:
                SDL_UnlockAudio()
                return i

        SDL_UnlockAudio()
        return -1

    def get_playing_sound_instance_by_id(self, sound_instance_id):
        if sound_instance_id in self._playing_sound_instances_by_id:
            return self._playing_sound_instances_by_id[sound_instance_id]
        else:
            return None

    def get_status(self):
        """
        Get the current track status (status of playlists on the track).
        Used for debugging and testing.
        Returns:
            A list of status dictionaries containing the current settings for playlists currently
            playing on the track.
        """
        SDL_LockAudio()
        status = []

        # TODO: Loop over any playing playlists and add their status to the list

        SDL_UnlockAudio()

        return status


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
    cdef void mix_playing_sounds(TrackState *track, Uint32 buffer_length, AudioCallbackData *callback_data) nogil:
        """
        Mixes any sounds that are playing on the specified playlist track into the specified audio buffer.
        Args:
            track: A pointer to the TrackState data structure for the track
            buffer_length: The length of the output buffer (in bytes)
            callback_data: The audio callback data structure
        Notes:
            Notification messages are generated.
        """
        cdef TrackState *target_track
        cdef TrackPlaylistState *playlist_track

        if track == NULL or track.type_state == NULL:
            return

        playlist_track = <TrackPlaylistState*>track.type_state

        # Setup local variables
        cdef Uint32 buffer_bytes_remaining
        cdef Uint32 current_chunk_bytes
        cdef Uint32 track_buffer_pos
        cdef Uint8 control_point
        cdef float progress

        # Loop over active playlist sounds

            # Set flag indicating there is at least some activity on the track (it is active)
            track.active = True

            track_buffer_pos = 0
            control_point = 0
            buffer_bytes_remaining = buffer_length

            # Loop over output buffer at control rate
            while buffer_bytes_remaining > 0:

                # Determine the number of bytes to process in the current chunk
                current_chunk_bytes = min(buffer_bytes_remaining, callback_data.bytes_per_control_point)

                # Calculate volume of chunk (handle fading)

                # Copy samples for chunk to output buffer and apply volume

                # Process markers (do any markers fall in the current chunk?)
                # Note: the current sample position has already been incremented when the sample data was received so
                # we need to look backwards from the current position to determine if marker falls in chunk window.

                        # Marker is in window, send notification

                    # Special check if buffer wraps back around to the beginning of the sample

                        # Marker is in window, send notification

                # Check if sound is finished due to a fade out completing

                # Sound finished processing

                # Move to next chunk
                buffer_bytes_remaining -= current_chunk_bytes
                track_buffer_pos += current_chunk_bytes
                control_point += 1

