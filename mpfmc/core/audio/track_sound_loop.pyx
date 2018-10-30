#!python
#cython: embedsignature=True, language_level=3

from libc.stdio cimport FILE, fopen, fprintf, sprintf, fflush, fclose
from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
cimport cpython.pycapsule as pycapsule
import cython
import logging
from math import ceil, floor

from mpfmc.core.audio.sdl2 cimport *
from mpfmc.core.audio.gstreamer cimport *
from mpfmc.core.audio.track cimport *
from mpfmc.core.audio.inline cimport in_out_quad
from mpfmc.core.audio.notification_message cimport *
from mpfmc.core.audio.track_sound_loop cimport *
from mpfmc.core.audio.audio_exception import AudioException


# ---------------------------------------------------------------------------
#    TrackSoundLoop class
# ---------------------------------------------------------------------------
cdef class TrackSoundLoop(Track):
    """
    Live Loop track class
    """

    def __init__(self, object mc, object audio_callback_data, str name, int track_num, int buffer_size,
                 int max_layers=8,
                 float volume=1.0):
        """
        Constructor
        Args:
            mc: The media controller app
            audio_callback_data: The AudioCallbackData struct wrapped in a PyCapsule
            name: The track name
            track_num: The track number
            buffer_size: The length of the track audio buffer in bytes
            max_layers: The maximum number of sounds that can be played simultaneously
                on the track
            volume: The track volume (0.0 to 1.0)
        """
        # IMPORTANT: Call super class init function to allocate track state memory!
        super().__init__(mc, audio_callback_data, name, track_num, buffer_size, volume)

        self.log = logging.getLogger("Track." + str(track_num) + ".TrackSoundLoop." + name)

        SDL_LockAudio()

        # Set track type specific settings
        self.state.mix_callback_function = TrackSoundLoop.mix_playing_sounds

        # Allocate memory for the specific track type state struct (TrackSoundLoopState)
        self.type_state = <TrackSoundLoopState*> PyMem_Malloc(sizeof(TrackSoundLoopState))
        self.state.type_state = <void*>self.type_state

        # Initialize track specific state structures
        self._initialize_player(&self.type_state.player_1)
        self._initialize_player(&self.type_state.player_2)
        self.type_state.current = cython.address(self.type_state.player_1)
        self.type_state.next = cython.address(self.type_state.player_2)

        self._sound_loop_set_counter = 0
        self._active_sound_loop_sets = dict()

        self.log.debug("Created Track %d %s", self.number, self.name)

        SDL_UnlockAudio()

    def __dealloc__(self):
        """Destructor"""

        SDL_LockAudio()

        # Free the specific track type state and other allocated memory
        if self.type_state != NULL:

            if self.type_state.player_1.layers != NULL:
                self._reset_player_layers(cython.address(self.type_state.player_1))

            if self.type_state.player_2.layers != NULL:
                self._reset_player_layers(cython.address(self.type_state.player_2))

            PyMem_Free(self.type_state)
            self.type_state = NULL
            if self.state != NULL:
                self.state.type_state = NULL

        SDL_UnlockAudio()

    def __repr__(self):
        return '<Track.{}.SoundLoop.{}>'.format(self.number, self.name)

    @property
    def type(self):
        return "sound_loop"

    @property
    def supports_in_memory_sounds(self):
        """Return whether or not track accepts in-memory sounds"""
        return True

    @property
    def supports_streaming_sounds(self):
        """Return whether or not track accepts streaming sounds"""
        return False

    cdef _initialize_player(self, SoundLoopSetPlayer *player):
        """Initializes a SoundLoopSetPlayer struct."""
        if player != NULL:
            player.status = player_idle
            player.length = 0
            player.master_sound_layer.status = layer_playing
            player.master_sound_layer.sound = NULL
            player.master_sound_layer.volume = 0
            player.master_sound_layer.sound_loop_set_id = 0
            player.master_sound_layer.sound_id = 0
            player.master_sound_layer.fade_in_steps = 0
            player.master_sound_layer.fade_out_steps = 0
            player.master_sound_layer.fade_steps_remaining = 0
            player.master_sound_layer.looping = True
            player.master_sound_layer.marker_count = 0
            player.master_sound_layer.markers = NULL
            player.layers = NULL
            player.sample_pos = 0
            player.stop_loop_at_pos = do_not_stop_loop

    def stop_all_sounds(self, float fade_out_seconds = 0.0):
        """
        Stops all playing sounds immediately on the track.
        Args:
            fade_out_seconds: The number of seconds to fade out the sounds before stopping
        """
        pass

    def stop_sound(self, sound not None, fade_out=None):
        """
        Stops all instances of the specified sound immediately on the track. This function is not used
        in the sound loop track, but is provided for compatibility in case the sound player is
        mistakenly used against this track.
        Args:
            sound: The Sound to stop
            fade_out: Optional amount of time (seconds) to fade out before stopping
        """
        pass

    def stop_sound_instance(self, sound_instance not None, fade_out=None):
        """
        Stops the specified sound instance immediately on the track. This function is not used
        in the sound loop track, but is provided for compatibility in case the sound player is
        mistakenly used against this track.
        Args:
            sound_instance: The SoundInstance to stop
            fade_out: Optional amount of time (seconds) to fade out before stopping
        """
        pass

    def stop_sound_looping(self, sound not None):
        """
        Cancels looping for all instances of the specified sound on the track. This function is not used
        in the sound loop track, but is provided for compatibility in case the sound player is
        mistakenly used against this track.
        Args:
            sound: The Sound to stop looping
        """
        pass

    def stop_sound_instance_looping(self, sound_instance not None):
        """
        Stops the specified sound instance on the track after the current loop iteration
        has finished. This function is not used in the sound loop track, but is provided for compatibility
        in case the sound player is mistakenly used against this track.
        Args:
            sound_instance: The Sound to stop
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
        if notification_message.message in (notification_track_stopped, notification_track_paused):
            if notification_message.message == notification_track_stopped:
                # Trigger any events
                if self._events_when_stopped is not None:
                    for event in self._events_when_stopped:
                        self.mc.post_mc_native_event(event, track=self._name)

            elif notification_message.message == notification_track_paused:
                # Trigger any events
                if self._events_when_paused is not None:
                    for event in self._events_when_paused:
                        self.mc.post_mc_native_event(event, track=self._name)
                pass

            SDL_UnlockAudio()
            return

        self.log.debug("Processing notification message %d for sound instance (id: %d)",
                       notification_message.message, notification_message.sound_instance_id)

        if notification_message.message in (notification_sound_loop_set_started, notification_sound_loop_set_stopped,
                                            notification_sound_loop_set_looping):

            if notification_message.data.sound_loop_set.id not in self._active_sound_loop_sets.keys():
                self.log.warning("Received a notification message for a sound loop set (id: %d) "
                                 "that is no longer active. Notification will be discarded.",
                                 notification_message.data.sound_loop_set.id)
                SDL_UnlockAudio()
                return

            sound_loop_set_settings = self._active_sound_loop_sets[notification_message.data.sound_loop_set.id]
            if not sound_loop_set_settings:
                self.log.warning("Could not retrieve settings for a sound loop set (id: %d) "
                                 "Notification will be discarded.",
                                 notification_message.data.sound_loop_set.id)
                SDL_UnlockAudio()
                return

            if notification_message.message == notification_sound_loop_set_started:
                if sound_loop_set_settings['events_when_played'] is not None:
                    for event in sound_loop_set_settings['events_when_played']:
                        self.mc.post_mc_native_event(event)

            elif notification_message.message == notification_sound_loop_set_stopped:
                if sound_loop_set_settings['events_when_stopped'] is not None:
                    for event in sound_loop_set_settings['events_when_stopped']:
                        self.mc.post_mc_native_event(event)

                self.log.debug("Removing sound_loop_set settings %d from active list", notification_message.data.sound_loop_set.id)
                del self._active_sound_loop_sets[notification_message.data.sound_loop_set.id]

            elif notification_message.message == notification_sound_loop_set_looping:
                if sound_loop_set_settings['events_when_looping'] is not None:
                    for event in sound_loop_set_settings['events_when_looping']:
                        self.mc.post_mc_native_event(event)

        elif notification_message.message == notification_sound_marker:

            if notification_message.sound_id not in self.mc.sounds_by_id.keys():
                self.log.warning("Received a notification message for a sound (id: %d) "
                                 "that does not exist. Notification will be discarded.",
                                 notification_message.sound_id)
                SDL_UnlockAudio()
                return

            # In a sound loop track, sound instances are not created when playing a loop sound.  The sound
            # asset is used directly and therefore we need to reference the sound asset by sound_id to
            # retrieve the marker events to send.
            sound = self.mc.sounds_by_id[notification_message.sound_id]

            # Send marker event(s)
            if sound and 0 <= notification_message.data.marker.id < sound.marker_count:
                if sound.markers[notification_message.data.marker.id]['events'] is not None:
                    for event in sound.markers[notification_message.data.marker.id]['events']:
                        self.mc.post_mc_native_event(event,
                                                     sound_instance=sound,
                                                     marker_id=notification_message.data.marker.id)

        SDL_UnlockAudio()

    def play_sound_loop_set(self, dict sound_loop_set not None, str context=None, dict player_settings=None):
        """
        Immediately play a sound loop set.

        Args:
            sound_loop_set: The sound_loop_set asset object to play.
            context: The context from which the sound loop set is played.
            player_settings: Settings to use for playback
        """
        cdef SoundLoopSetPlayer *player
        cdef SoundLoopLayerSettings *layer
        cdef int bytes_per_sample_frame
        cdef bint player_already_playing = False

        self.log.debug("play_sound_loop_set - Preparing sound_loop_set '%s' for playback.", sound_loop_set)

        if player_settings is None:
            player_settings = dict()

        # Determine settings (override sound loop set with player settings)
        player_settings.setdefault('fade_in', sound_loop_set['fade_in'])
        player_settings.setdefault('fade_out', sound_loop_set['fade_out'])
        player_settings.setdefault('start_at', 0)
        player_settings.setdefault('events_when_played', sound_loop_set['events_when_played'])
        player_settings.setdefault('events_when_stopped', sound_loop_set['events_when_stopped'])
        player_settings.setdefault('events_when_looping', sound_loop_set['events_when_looping'])
        player_settings.setdefault('mode_end_action', sound_loop_set['mode_end_action'])
        player_settings.setdefault('tempo', sound_loop_set['tempo'])
        player_settings.setdefault('timing', 'loop_end')
        player_settings.setdefault('interval', 1)
        player_settings.setdefault('synchronize', False)
        player_settings['sound'] = sound_loop_set['sound']
        player_settings['context'] = context

        # print("play_sound_loop_set - player_settings:", player_settings)

        if player_settings['sound'] not in self.mc.sounds:
            self.log.error("play_sound_loop_set - sound %s in sound_loop_set could "
                           "not be located, could not play loop set", player_settings['sound'])
            return

        if not self.mc.sounds[player_settings['sound']].loaded:
            self.log.error("play_sound_loop_set - sound %s in sound_loop_set was "
                           "not loaded, could not play loop set", player_settings['sound'])
            return

        SDL_LockAudio()

        # Determine current track player status so we can determine what action(s) should be
        # taken to play the requested loop set.  There should never be a situation where the
        # current player is idle while the next one is playing.
        if self.type_state.current.status == player_idle:

            # The current player is idle.  This is the simplest case as the queue and
            # synchronize settings can be ignored as we simply start playing the requested
            # loop set immediately on the current player.
            player = self.type_state.current
            self._reset_player_layers(player)
            player_already_playing = False
            player.stop_loop_at_pos = do_not_stop_loop

        elif self.type_state.next.status in (player_idle, player_pending):

            # The current player is busy playing a loop set.  In this case the queue and
            # synchronize settings are important and dictate how the requested loop set
            # will be played.
            player = self.type_state.next
            self._reset_player_layers(player)
            player_already_playing = True

            # Remove the previously pending sound_loop_set from the active sound loop set dict (if exists)
            if self.type_state.next.status == player_pending and player.master_sound_layer.sound_loop_set_id in self._active_sound_loop_sets:
                del self._active_sound_loop_sets[player.master_sound_layer.sound_loop_set_id]

        else:
            # TODO: Handle case when both players are busy (i.e. during a cross-fade)
            self.log.info("Unable to play sound - both sound loop players are currently busy.")
            # print("Unable to play sound - both sound loop players are currently busy.")
            SDL_UnlockAudio()
            return

        # print("play_sound_loop_set - player_already_playing:", player_already_playing)

        # Calculate fading (done at control rate; need to calculate the number of steps over which to fade in/out)
        player.master_sound_layer.fade_in_steps = player_settings['fade_in'] * self.state.callback_data.seconds_to_bytes_factor // self.state.callback_data.bytes_per_control_point
        player.master_sound_layer.fade_out_steps = player_settings['fade_out'] * self.state.callback_data.seconds_to_bytes_factor // self.state.callback_data.bytes_per_control_point
        player.master_sound_layer.fade_steps_remaining = player.master_sound_layer.fade_in_steps
        
        if player_already_playing:

            # Determine if playing immediately or queuing until next loop
            if player_settings['timing'] == 'loop_end':
                # Queue until the end of the current loop
                player.status = player_pending
                player.sample_pos = player_settings['start_at'] * self.state.callback_data.seconds_to_bytes_factor

                # Ensure sample position starts on a sample frame boundary (audio distortion may occur if starting
                # in the middle of a sample frame)
                bytes_per_sample_frame = self.state.callback_data.bytes_per_sample * self.state.callback_data.channels
                player.sample_pos = bytes_per_sample_frame * ceil(player.sample_pos / bytes_per_sample_frame)

                self.type_state.current.stop_loop_at_pos = self.type_state.current.length

            elif player_settings['timing'] == 'next_time_interval':
                # Set currently playing sample to end at the next specified time interval multiple
                player.status = player_pending
                self.type_state.current.stop_loop_at_pos = self._round_sample_pos_up_to_interval(
                    self.type_state.current.sample_pos,
                    <Uint32>(self.state.callback_data.seconds_to_bytes_factor * player_settings['interval']),
                    self.state.callback_data.bytes_per_sample * self.state.callback_data.channels)

                # Adjust currently playing sample end position to ensure it is within the sample
                while self.type_state.current.stop_loop_at_pos > self.type_state.current.length:
                    self.type_state.current.stop_loop_at_pos -= self.type_state.current.length

                # If stop position is at beginning of loop (first 10ms), set it to be the end so it won't start
                # another iteration of the loop (probably a rounding error anyway)
                if self.type_state.current.stop_loop_at_pos < <Uint32>(0.01 * self.state.callback_data.seconds_to_bytes_factor):
                    self.type_state.current.stop_loop_at_pos = self.type_state.current.length

                # print("play_sound_loop_set - next_time_interval - sample_pos, stop_loop_at_pos, length:", self.type_state.current.sample_pos, self.type_state.current.stop_loop_at_pos, self.type_state.current.length)

            elif player_settings['timing'] == 'next_beat_interval':
                # Set currently playing sample to end at the next specified beat interval multiple
                player.status = player_pending
                self.type_state.current.stop_loop_at_pos = self._round_sample_pos_up_to_interval(
                    self.type_state.current.sample_pos,
                    <Uint32> (self.state.callback_data.seconds_to_bytes_factor * (
                            player_settings['interval'] * 60.0 / self.type_state.current.tempo)),
                    self.state.callback_data.bytes_per_sample * self.state.callback_data.channels)

                # Adjust currently playing sample end position to ensure it is within the sample
                while self.type_state.current.stop_loop_at_pos > self.type_state.current.length:
                    self.type_state.current.stop_loop_at_pos -= self.type_state.current.length

                # If stop position is at beginning of loop (first 10ms), set it to be the end so it won't start
                # another iteration of the loop (probably a rounding error anyway)
                if self.type_state.current.stop_loop_at_pos < <Uint32>(0.01 * self.state.callback_data.seconds_to_bytes_factor):
                    self.type_state.current.stop_loop_at_pos = self.type_state.current.length

            else:
                # Play now

                # Synchronize the loop set to the current player (if flag is set)
                if player_settings['synchronize']:
                    player.sample_pos = self.type_state.current.sample_pos

                    # If no fade is set, use a quick cross-fade when synchronizing
                    # (avoids pops & clicks)
                    if player.master_sound_layer.fade_steps_remaining == 0:
                        player.master_sound_layer.fade_in_steps = self.state.callback_data.quick_fade_steps
                        player.master_sound_layer.fade_steps_remaining = player.master_sound_layer.fade_in_steps
                else:
                    player.sample_pos = 0
                    # TODO: Add a quick fade out to current player then start new one

                if player.master_sound_layer.fade_steps_remaining > 0:
                    player.status = player_fading_in
                    self.type_state.current.status = player_fading_out
                    self.type_state.current.master_sound_layer.fade_out_steps = player.master_sound_layer.fade_in_steps
                    self.type_state.current.master_sound_layer.fade_steps_remaining = player.master_sound_layer.fade_steps_remaining

                else:
                    player.status = player_playing

        else:
            if player.master_sound_layer.fade_steps_remaining > 0:
                player.status = player_fading_in
            else:
                player.status = player_playing

        player.sample_pos = player_settings['start_at'] * self.state.callback_data.seconds_to_bytes_factor

        # Save current sound loop set so it can be referred to again while it is active (event notifications)
        self._sound_loop_set_counter += 1
        self._active_sound_loop_sets[self._sound_loop_set_counter] = player_settings

        master_layer_settings = {
            "sound_loop_set_id": self._sound_loop_set_counter,
            "sound": sound_loop_set['sound'],
            "volume": sound_loop_set['volume'],
            "initial_state": "play"
        }

        self._apply_layer_settings(&player.master_sound_layer, master_layer_settings)

        # Determine master sound length
        if player.master_sound_layer.sound != NULL:
            player.length = <Uint32>player.master_sound_layer.sound.data.memory.size
            player.tempo = player_settings['tempo']

            # Adjust sample position to ensure it is within the sample
            while player.sample_pos >= player.length:
                player.sample_pos -= player.length
        else:
            player.length = 0
            player.sample_pos = 0
            player.status = player_idle

        # Setup sound loop set layers
        for layer_settings in sound_loop_set['layers']:
            layer = _create_sound_loop_layer_settings()
            self._apply_layer_settings(layer, layer_settings)

            # Layer fading is only set by events using the sound_loop_player
            layer.fade_in_steps = 0
            layer.fade_out_steps = 0
            layer.fade_steps_remaining = 0

            # Append layer
            player.layers = g_slist_append(player.layers, layer)

        # Send sound_loop_set started notification (if not pending/queued)
        if player.status not in (player_idle, player_pending):
            send_sound_loop_set_started_notification(player.master_sound_layer.sound_loop_set_id,
                                                     player.master_sound_layer.sound_id,
                                                     self.state)
            # send_sound_started_notification(0, player.master_sound_layer.sound_id, 0, self.state)

        SDL_UnlockAudio()

    cdef _apply_layer_settings(self, SoundLoopLayerSettings *layer, dict layer_settings):
        cdef SoundFile sound_container

        if 'initial_state' not in layer_settings or layer_settings['initial_state'] == 'play':
            layer.status = layer_playing
        else:
            layer.status = layer_stopped

        if 'sound_loop_set_id' in layer_settings:
            layer.sound_loop_set_id = layer_settings['sound_loop_set_id']
        else:
            layer.sound_loop_set_id = 0

        # Set layer sound
        sound = self.mc.sounds[layer_settings['sound']]

        # TODO: What to do when sound is not loaded?
        # TODO: Perhaps load sounds and delay play until loaded?

        sound_container = sound.container
        layer.sound = cython.address(sound_container.sample)
        layer.sound_id = sound.id

        # By default, all layers will continue to loop when played
        layer.looping = True

        # Layer volume (multiply layer setting by sound setting or use sound setting if None)
        if layer_settings['volume']:
            layer.volume = <Uint8>(min(layer_settings['volume'] * sound.volume * SDL_MIX_MAXVOLUME), SDL_MIX_MAXVOLUME)
        else:
            layer.volume = <Uint8>(min(sound.volume * SDL_MIX_MAXVOLUME), SDL_MIX_MAXVOLUME)

        # Markers (copy from source sound)
        layer.marker_count = sound.marker_count

        if layer.marker_count > 0:
            layer.markers = g_array_new(False, False, sizeof(guint))
            g_array_set_size(layer.markers, sound.marker_count)
            for index in range(sound.marker_count):
                g_array_insert_val_uint(layer.markers,
                                        index,
                                        <guint>(sound.markers[index]['time'] * self.state.callback_data.seconds_to_bytes_factor))

    def stop_current_sound_loop_set(self, fade_out=None):
        """
        Stops the currently playing sound loop set.
        Args:
            fade_out: The number of seconds over which to fade out the currently playing
                      sound loop set before stopping.
        """
        SDL_LockAudio()

        self.log.debug("Stopping current sound loop set")

        if self.type_state.current.status not in (player_playing, player_fading_in, player_fading_out):
            self.log.info("Unable to stop sound loop set - no sound loop set is currently playing.")
            SDL_UnlockAudio()
            return

        # Calculate new fade out if specified (overriding current setting)
        if fade_out:
            self.type_state.current.master_sound_layer.fade_out_steps = fade_out * self.state.callback_data.seconds_to_bytes_factor // self.state.callback_data.bytes_per_control_point

        # If no fade out is specified, perform quick fade out
        if self.type_state.current.master_sound_layer.fade_out_steps == 0:
            self.type_state.current.master_sound_layer.fade_out_steps = self.state.callback_data.quick_fade_steps

        self.type_state.current.master_sound_layer.fade_steps_remaining = self.type_state.current.master_sound_layer.fade_out_steps
        self.type_state.current.status = player_fading_out

        # Need to check if the next sound player has a loop set queued for playback and if so, cancel it
        if self.type_state.next.status == player_pending:
            self.type_state.next.status = player_idle
            self.type_state.next.master_sound_layer.sound_loop_set_id = 0
            self.type_state.next.master_sound_layer.sound_id = 0

        elif self.type_state.next.status == player_fading_out:
            # Do we need to shorted the current fade-out?
            if self.type_state.next.master_sound_layer.fade_steps_remaining > self.type_state.current.master_sound_layer.fade_steps_remaining:
                self.type_state.next.master_sound_layer.fade_steps_remaining = self.type_state.current.master_sound_layer.fade_steps_remaining

        SDL_UnlockAudio()

    def jump_to_time_current_sound_loop_set(self, time=0.0):
        """Immediately jumps the loop playback position to the specified time."""

        SDL_LockAudio()

        self.log.debug("Jumping to %f seconds playback position in current sound loop set")

        if self.type_state.current.status not in (player_playing, player_fading_in, player_fading_out):
            self.log.info("Unable to jump to specified playback position - "
                          "no sound loop set is currently playing.")
            SDL_UnlockAudio()
            return

        # Set new playback position (make sure it is within the current sample length)
        self.type_state.current.sample_pos = time * self.state.callback_data.seconds_to_bytes_factor
        while self.type_state.current.sample_pos >= self.type_state.current.length:
            self.type_state.current.sample_pos -= self.type_state.current.length

        SDL_UnlockAudio()

    def stop_looping_current_sound_loop_set(self):
        """
        Stops the currently playing sound loop set from continuing to loop (it will stop
        after the current loop iteration).
        """
        SDL_LockAudio()

        self.log.debug("Stopping looping current sound loop set")

        if self.type_state.current.status not in (player_playing, player_fading_in, player_fading_out):
            self.log.info("Unable to stop looping sound loop set - no sound loop set is currently playing.")
            SDL_UnlockAudio()
            return

        self.type_state.current.master_sound_layer.looping = False
        self.type_state.current.stop_loop_at_pos = self.type_state.current.length

        SDL_UnlockAudio()

    def play_layer(self, int layer, float fade_in=0.0, str timing="loop_end", volume=None):
        """
        Plays the specified layer number in the currently playing sound loop set.

        Args:
            layer: The layer number to play (1-based array position).
            fade_in: The number of seconds over which to fade in the layer.
            timing: Flag indicating whether the layer should be played immediately ('now')
                    or queued until the next loop of the master layer loop ('loop_end').
            volume: The layer volume (overrides sound loop set setting if not None)
        """
        cdef SoundLoopLayerSettings *layer_settings

        if layer < 1:
            self.log.warning("Illegal layer value in call to play_layer (must be > 0).")
            return

        SDL_LockAudio()

        self.log.debug("play_layer - Play layer %d of the currently playing sound_loop_set (fade-in = %f sec).",
                       layer, fade_in)

        # Retrieve the layer
        if self.type_state.current.layers == NULL:
            self.log.info("There are no layers defined in the current sound loop set: play_layers has no effect")
            SDL_UnlockAudio()
            return

        layer_settings = <SoundLoopLayerSettings*>g_slist_nth_data(self.type_state.current.layers, layer - 1)
        if layer_settings == NULL:
            self.log.info("The specified layer could not be found in the current sound loop set: play_layers has no effect")
            SDL_UnlockAudio()
            return

        if layer_settings.status != layer_stopped:
            self.log.info("The current sound loop set layer is already playing: play_layers has no effect")
            SDL_UnlockAudio()
            return

        # Layer volume (use layer settings or sound setting if None)
        if volume:
            layer_settings.volume = <Uint8>(volume * SDL_MIX_MAXVOLUME)

        # Calculate fading (done at control rate; need to calculate the number of steps over which to fade in/out)
        if fade_in > 0.0:
            layer_settings.fade_in_steps = <Uint32>(fade_in * self.state.callback_data.seconds_to_bytes_factor) // self.state.callback_data.bytes_per_control_point
            layer_settings.fade_steps_remaining = layer_settings.fade_in_steps

        if timing == 'loop_end':
            layer_settings.status = layer_queued

        elif timing == 'now':
            if layer_settings.fade_in_steps > 0:
                layer_settings.status = layer_fading_in
            else:
                layer_settings.status = layer_playing
        else:
            self.log.error("Unknown timing value specified: %s", timing)
            SDL_UnlockAudio()
            return

        layer_settings.looping = True

        SDL_UnlockAudio()

    def stop_layer(self, int layer, float fade_out=0.0):
        """
        Stops the specified layer number in the currently playing sound loop set.

        Args:
            layer: The layer number to stop (1-based array position).
            fade_out: The number of seconds over which to fade out the layer before stopping.
        """
        cdef SoundLoopLayerSettings *layer_settings

        if layer < 1:
            self.log.warning("Illegal layer value in call to stop_layer (must be > 0).")
            return

        SDL_LockAudio()

        self.log.debug("stop_layer - Stop layer %d of the currently playing sound_loop_set (fade-out = %f sec).",
                       layer, fade_out)

        # Retrieve the layer
        if self.type_state.current.layers == NULL:
            self.log.info("There are no layers defined in the current sound loop set: stop_layers has no effect")
            SDL_UnlockAudio()
            return

        layer_settings = <SoundLoopLayerSettings*>g_slist_nth_data(self.type_state.current.layers, layer - 1)
        if layer_settings == NULL:
            self.log.info("The specified layer could not be found in the current sound loop set: stop_layers has no effect")
            SDL_UnlockAudio()
            return

        if layer_settings.status == layer_stopped:
            self.log.info("The current sound loop set layer is already stopped: stop_layers has no effect")
            SDL_UnlockAudio()
            return

        # Calculate fading (done at control rate; need to calculate the number of steps over which to fade in/out)
        if fade_out > 0.0:
            layer_settings.fade_out_steps = <Uint32>(fade_out * self.state.callback_data.seconds_to_bytes_factor) // self.state.callback_data.bytes_per_control_point
            layer_settings.fade_steps_remaining = layer_settings.fade_out_steps
            layer_settings.status = layer_fading_out
        else:
            # TODO: Could perform a quick fade out rather than an abrupt stop
            layer_settings.status = layer_stopped

        SDL_UnlockAudio()

    def stop_looping_layer(self, int layer):
        """
        Stops the specified layer number in the currently playing sound loop set after
        the currently playing loop finishes.

        Args:
            layer: The layer number to stop looping (1-based array position).
        """
        cdef SoundLoopLayerSettings *layer_settings

        if layer < 1:
            self.log.warning("Illegal layer value in call to stop_looping_layer (must be > 0).")
            return

        SDL_LockAudio()

        self.log.debug("stop_looping_layer - Stop looping layer %d of the currently playing sound_loop_set.", layer)

        # Retrieve the layer
        if self.type_state.current.layers == NULL:
            self.log.info("There are no layers defined in the current sound loop set: "
                          "stop_looping_layers has no effect")
            SDL_UnlockAudio()
            return

        layer_settings = <SoundLoopLayerSettings*>g_slist_nth_data(self.type_state.current.layers, layer - 1)
        if layer_settings == NULL:
            self.log.info("The specified layer could not be found in the current sound loop set: "
                          "stop_looping_layers has no effect")
            SDL_UnlockAudio()
            return

        if layer_settings.status == layer_stopped:
            self.log.info("The current sound loop set layer is already stopped: "
                          "stop_looping_layers has no effect")
            SDL_UnlockAudio()
            return

        layer_settings.looping = False

        SDL_UnlockAudio()

    cdef _reset_layer(self, SoundLoopLayerSettings *layer):
        """Reset (free memory) for a single sound loop set layer."""
        if layer != NULL:
            if layer.markers != NULL:
                g_array_free(layer.markers, True)
                layer.markers = NULL

    cdef _reset_player_layers(self, SoundLoopSetPlayer *player):
        """Reset (free memory) for sound loop set player layers."""
        if player != NULL:
            self._reset_layer(&player.master_sound_layer)

            if player.layers != NULL:
                iterator = player.layers
                while iterator != NULL:
                    layer = <SoundLoopLayerSettings*>iterator.data
                    self._reset_layer(layer)
                    g_slice_free1(sizeof(SoundLoopLayerSettings), layer)
                    iterator = iterator.next

                g_slist_free(player.layers)
                player.layers = NULL

    def get_status(self):
        """
        Get the current track status (status of all sound loop players on the track).
        Used for debugging and testing.
        Returns:
            A list of status dictionaries containing the current settings for each
            sound loop player.
        """
        cdef SoundLoopSetPlayer *player
        cdef SoundLoopLayerSettings *layer
        cdef int index = 0

        SDL_LockAudio()
        status = []
        for player_num in range(2):
            if player_num == 0:
                player = self.type_state.current
            else:
                player = self.type_state.next

            if player == NULL:
                status.append({
                    "status": TrackSoundLoop.player_status_to_text(player_idle),
                    "length": 0
                })
            else:
                layers = []
                layer = <SoundLoopLayerSettings*>g_slist_nth_data(player.layers, index)
                while layer != NULL:
                    layers.append({
                        "status": TrackSoundLoop.layer_status_to_text(layer.status),
                        "sound_id": layer.sound_id,
                        "sound_length": layer.sound.data.memory.size,
                        "volume": layer.volume,
                        "fade_in_steps": layer.fade_in_steps,
                        "fade_out_steps": layer.fade_out_steps,
                        "fade_steps_remaining": layer.fade_steps_remaining,
                        "looping": layer.looping,
                        "marker_count": layer.marker_count,
                    })
                    index += 1
                    layer = <SoundLoopLayerSettings*>g_slist_nth_data(player.layers, index)

                status.append({
                    "status": TrackSoundLoop.player_status_to_text(<int>player.status),
                    "length": player.length,
                    "sound_id": player.master_sound_layer.sound_id,
                    "volume": player.master_sound_layer.volume,
                    "layers": layers,
                    "sample_pos": player.sample_pos,
                    "stop_loop_at_pos": player.stop_loop_at_pos,
                    "fade_in_steps": player.master_sound_layer.fade_in_steps,
                    "fade_out_steps": player.master_sound_layer.fade_out_steps,
                    "fade_steps_remaining": player.master_sound_layer.fade_steps_remaining,
                    "looping": player.master_sound_layer.looping,
                })

        SDL_UnlockAudio()

        return status

    @staticmethod
    def player_status_to_text(int status):
        """
        Converts a sound loop player status value into an equivalent text string.  Used for testing
        purposes only.
        Args:
            status: Integer sound loop player status value

        Returns:
            string containing the equivalent status text
        """
        status_values = {
            player_idle: "idle",
            player_pending: "pending",
            player_playing: "playing",
            player_fading_in: "fading in",
            player_fading_out: "fading out",
        }

        try:
            return status_values.get(status)
        except KeyError:
            return "unknown"

    @staticmethod
    def layer_status_to_text(int status):
        """
        Converts a sound loop set layer status value into an equivalent text string.  Used for testing
        purposes only.
        Args:
            status: Integer sound loop set layer status value

        Returns:
            string containing the equivalent status text
        """
        status_values = {
            layer_stopped: "stopped",
            layer_queued: "queued",
            layer_playing: "playing",
            layer_fading_in: "fading in",
            layer_fading_out: "fading out",
        }

        try:
            return status_values.get(status)
        except KeyError:
            return "unknown"

    cdef inline Uint32 _round_sample_pos_up_to_interval(self, Uint32 sample_pos, Uint32 interval, int bytes_per_sample_frame):
        """
        Rounds sample position up to the nearest specified interval.
        
        Args:
            sample_pos: The sample position value to round up. 
            interval: The interval to round up to.
            bytes_per_sample_frame: The number of bytes per sample frame (a frame includes a single sample
                for each channel in the audio).

        Returns:
            Sample position rounded up to the nearest specified interval.
            
        Notes:
            The number of audio channels is important in this function so we do not split a sample frame in
            the middle of its bytes (would cause unwanted audio artifacts). Buffers are only split on
            a whole sample frame boundary.
        """
        return bytes_per_sample_frame * ceil((interval * ceil(sample_pos / interval)) / bytes_per_sample_frame)


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
        cdef TrackSoundLoopState *sound_loop_track
        cdef bint first_layer = True
        cdef bint switch_players = False
        cdef bint reset_track_buffer_pos = True
        cdef SoundLoopSetPlayer *player

        if track == NULL or track.type_state == NULL:
            return

        sound_loop_track = <TrackSoundLoopState*>track.type_state

        # Setup local variables
        cdef Uint32 track_buffer_pos

        # If the current player is idle, the track is not active so there is nothing to do
        if sound_loop_track.current == NULL or sound_loop_track.current.status == player_idle:
            return

        # Set flag indicating there is at least some activity on the track (it is active)
        track.active = True

        # Process the current loop player (fill the track buffer with samples)
        track_buffer_pos = 0
        while track_buffer_pos < buffer_length and sound_loop_track.current.status \
                in (player_playing, player_fading_in, player_fading_out):

            track_buffer_pos = get_player_sound_samples(track, sound_loop_track.current,
                                                        buffer_length, track_buffer_pos,
                                                        callback_data)

            # Determine if we have reached the stop position for the loop (might not be at the end).
            if sound_loop_track.current.sample_pos == sound_loop_track.current.stop_loop_at_pos:

                sound_loop_track.current.status = player_idle

                # Send stopped notification
                send_sound_loop_set_stopped_notification(sound_loop_track.current.master_sound_layer.sound_loop_set_id,
                                                         sound_loop_track.current.master_sound_layer.sound_id,
                                                         track)

                # This player has finished, switch the other player to current at the end of this method 
                switch_players = True
                
                # If the other player has a sound loop pending, set the variables to start it playing
                if sound_loop_track.next.status == player_pending:
                    reset_track_buffer_pos = False
                    sound_loop_track.next.status = player_playing
                    send_sound_loop_set_started_notification(sound_loop_track.next.master_sound_layer.sound_loop_set_id,
                                                             sound_loop_track.next.master_sound_layer.sound_id,
                                                             track)

            # Determine if sound should continue to loop
            elif sound_loop_track.current.sample_pos >= sound_loop_track.current.length:

                    # Send looping notification
                    send_sound_loop_set_looping_notification(sound_loop_track.current.master_sound_layer.sound_loop_set_id,
                                                             sound_loop_track.current.master_sound_layer.sound_id,
                                                             track)
                    sound_loop_track.current.sample_pos = 0

        if reset_track_buffer_pos:
            track_buffer_pos = 0

        # Now process the next player
        while track_buffer_pos < buffer_length and sound_loop_track.next.status \
                in (player_playing, player_fading_in, player_fading_out):

            track_buffer_pos = get_player_sound_samples(track, sound_loop_track.next,
                                                        buffer_length, track_buffer_pos,
                                                        callback_data)

            # NOTE: It is not possible for the next loop player to have a stop position set (only
            #       the current loop player can have stop_loop_at_pos set) so we don't need to
            #       check it.

            # Check if we have reached the end of the sound loop.
            if sound_loop_track.next.sample_pos >= sound_loop_track.next.length:
                # End of sound loop reached, the next player will always loop
                send_sound_loop_set_looping_notification(sound_loop_track.next.master_sound_layer.sound_loop_set_id,
                                                         sound_loop_track.next.master_sound_layer.sound_id,
                                                         track)
                sound_loop_track.next.sample_pos = 0

            # Check if sound loop has finished playing/fading out
            if sound_loop_track.next.status == player_idle:
                # Sound stopped, send notification
                send_sound_loop_set_stopped_notification(sound_loop_track.next.master_sound_layer.sound_loop_set_id,
                                                         sound_loop_track.next.master_sound_layer.sound_id,
                                                         track)

        # Switch current and next players (if necessary)
        if switch_players:
            player = sound_loop_track.current
            sound_loop_track.current = sound_loop_track.next
            sound_loop_track.next = player

cdef Uint32 get_player_sound_samples(TrackState *track, SoundLoopSetPlayer *player,
                                     Uint32 buffer_length, Uint32 track_buffer_pos,
                                     AudioCallbackData *callback_data) nogil:
    """
    Retrieves and copies samples from the source sound to fill the track buffer.
     
    Args:
        track: 
        player: 
        buffer_length: 
        track_buffer_pos: 
        callback_data: 

    Returns:
        The updated track buffer position.
        
    Notes:
        The main loop fills the output buffer in chunks that are as large as possible, up to a maximum
        of the buffer length.  The chunks will be smaller during fading as each chunk will be at
        the same volume level (volume is updated at control rate and not audio rate). Also, if a
        sound finishes the chunk will only be big enough for the tail end of the sound.  This means
        it is possible to have a chunk that is only one sample long.
    """

    cdef SoundLoopLayerSettings *layer
    cdef GSList *layer_iterator
    cdef Uint8 player_volume, layer_volume
    cdef Uint32 layer_sample_pos, layer_bytes_remaining, layer_chunk_bytes, current_chunk_bytes, temp_chunk_bytes
    cdef Uint32 layer_track_buffer_pos_offset
    cdef Uint32 buffer_bytes_remaining = buffer_length - track_buffer_pos

    # Loop over the output buffer
    while buffer_bytes_remaining > 0:

        # Mix current player into track buffer.  Processing is done at control rate during player
        # fading and using full buffer when no fading is occurring.

        # Calculate the size and volume of chunk (handle fading)
        if player.status == player_fading_in:
            current_chunk_bytes = min(buffer_bytes_remaining,
                                      player.length - player.sample_pos,
                                      callback_data.bytes_per_control_point)
            player_volume = <Uint8> (in_out_quad((player.master_sound_layer.fade_in_steps - player.master_sound_layer.fade_steps_remaining) / player.master_sound_layer.fade_in_steps) * SDL_MIX_MAXVOLUME)
            player.master_sound_layer.fade_steps_remaining -= 1
            if player.master_sound_layer.fade_steps_remaining == 0:
                player.status = player_playing

        elif player.status == player_fading_out:
            current_chunk_bytes = min(buffer_bytes_remaining,
                                      player.length - player.sample_pos,
                                      callback_data.bytes_per_control_point)
            player_volume = <Uint8> (in_out_quad(player.master_sound_layer.fade_steps_remaining / player.master_sound_layer.fade_out_steps) * SDL_MIX_MAXVOLUME)
            player.master_sound_layer.fade_steps_remaining -= 1
            if player.master_sound_layer.fade_steps_remaining == 0:
                player.status = player_idle
        else:
            current_chunk_bytes = min(buffer_bytes_remaining, player.length - player.sample_pos)
            player_volume = SDL_MIX_MAXVOLUME

        # Adjust chunk size if the loop is set to stop early (if not the chunk size will remain unchanged)
        if player.sample_pos < player.stop_loop_at_pos:
            current_chunk_bytes = min(current_chunk_bytes, player.stop_loop_at_pos - player.sample_pos)

        if player.status == player_idle:
            return buffer_length

        # Get master layer samples
        SDL_MixAudioFormat(track.buffer + track_buffer_pos,
                           <Uint8*>player.master_sound_layer.sound.data.memory.data + player.sample_pos,
                           track.callback_data.format,
                           current_chunk_bytes,
                           player_volume * player.master_sound_layer.volume // SDL_MIX_MAXVOLUME)

        # Process markers (do any markers fall in the current chunk?)
        # Note: the current sample position has already been incremented when the sample data was received so
        # we need to look backwards from the current position to determine if marker falls in chunk window.
        for marker_id in range(player.master_sound_layer.marker_count):
            if player.sample_pos - current_chunk_bytes <= g_array_index_uint(player.master_sound_layer.markers, marker_id) < player.sample_pos:
                # Marker is in window, send notification
                send_sound_marker_notification(0,
                                               player.master_sound_layer.sound_id,
                                               player.master_sound_layer.sound_loop_set_id,
                                               track,
                                               marker_id)

        # Now mix any additional loop layers
        layer_iterator = player.layers
        while layer_iterator != NULL:
            layer = <SoundLoopLayerSettings*>layer_iterator.data

            if player.sample_pos == 0:

                if layer.status == layer_queued:
                    layer.status = layer_playing

                if not layer.looping:
                    layer.status = layer_stopped

            if layer.status in (layer_playing, layer_fading_in, layer_fading_out):
                layer_track_buffer_pos_offset = 0
                layer_sample_pos = player.sample_pos
                layer_bytes_remaining = current_chunk_bytes

                while layer_bytes_remaining > 0:
                    if layer.status == layer_playing:
                        layer_chunk_bytes = layer_bytes_remaining
                        layer_volume = layer.volume
                    else:
                        # Calculate layer volume (handle fading)
                        layer_chunk_bytes = min(callback_data.bytes_per_control_point, layer_bytes_remaining)
                        if layer.status == layer_fading_in:
                            layer_volume = <Uint8> (in_out_quad((layer.fade_in_steps - layer.fade_steps_remaining) / layer.fade_in_steps) * layer.volume)
                            layer.fade_steps_remaining -= 1
                            if layer.fade_steps_remaining == 0:
                                layer.status = layer_playing
                        elif layer.status == layer_fading_out:
                            layer_volume = <Uint8> (in_out_quad(layer.fade_steps_remaining / layer.fade_out_steps) * layer.volume)
                            layer.fade_steps_remaining -= 1
                            if layer.fade_steps_remaining == 0:
                                layer.status = layer_stopped
                                layer_bytes_remaining = 0

                    if layer_sample_pos < layer.sound.data.memory.size:
                        SDL_MixAudioFormat(track.buffer + track_buffer_pos + layer_track_buffer_pos_offset,
                                           <Uint8*>layer.sound.data.memory.data + layer_sample_pos,
                                           callback_data.format,
                                           min(layer_chunk_bytes, layer.sound.data.memory.size - layer_sample_pos),
                                           player_volume * layer_volume // SDL_MIX_MAXVOLUME)

                        # Process markers (do any markers fall in the current chunk?)
                        # Note: the current sample position has already been incremented when the sample data was received so
                        # we need to look backwards from the current position to determine if marker falls in chunk window.
                        for marker_id in range(layer.marker_count):
                            if layer_sample_pos - layer_chunk_bytes <= g_array_index_uint(layer.markers, marker_id) < layer_sample_pos:
                                # Marker is in window, send notification
                                send_sound_marker_notification(0,
                                                               layer.sound_id,
                                                               layer.sound_loop_set_id,
                                                               track,
                                                               marker_id)

                    layer_track_buffer_pos_offset += layer_chunk_bytes
                    layer_sample_pos += layer_chunk_bytes
                    layer_bytes_remaining -= layer_chunk_bytes

            # Move to next layer
            layer_iterator = layer_iterator.next

        # Advance buffer pointers
        player.sample_pos += current_chunk_bytes
        track_buffer_pos += current_chunk_bytes
        buffer_bytes_remaining -= current_chunk_bytes

        # Stop looping and generating samples if we have reached the end of the sound or
        # the player is now idle (due to reaching end of a fade out)
        if player.status == player_idle or \
                player.sample_pos >= player.length or \
                player.sample_pos == player.stop_loop_at_pos:
            break

    return track_buffer_pos


cdef inline SoundLoopLayerSettings *_create_sound_loop_layer_settings() nogil:
    """
    Creates a new sound loop layer settings struct.
    :return: A pointer to the new settings struct.
    """
    return <SoundLoopLayerSettings*>g_slice_alloc0(sizeof(SoundLoopLayerSettings))
