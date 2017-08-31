#!python
#cython: embedsignature=True, language_level=3

from libc.stdio cimport FILE, fopen, fprintf, sprintf, fflush, fclose
from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
cimport cpython.pycapsule as pycapsule
import cython
import logging

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
        self.type_state.current = cython.address(self.type_state.player_1)
        self.type_state.next = cython.address(self.type_state.player_2)

        self._initialize_player(self.type_state.current)
        self._initialize_player(self.type_state.next)

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
            player.master_sound_layer.sound_id = 0
            player.master_sound_layer.fade_in_steps = 0
            player.master_sound_layer.fade_out_steps = 0
            player.master_sound_layer.fade_steps_remaining = 0
            player.master_sound_layer.looping = True
            player.master_sound_layer.marker_count = 0
            player.master_sound_layer.markers = NULL
            player.layers = NULL
            player.sample_pos = 0

    def stop_all_sounds(self, float fade_out_seconds = 0.0):
        """
        Stops all playing sounds immediately on the track.
        Args:
            fade_out_seconds: The number of seconds to fade out the sounds before stopping
        """
        pass

    def process(self):
        """Processes the track queue each tick."""
        pass

    def play_sound_loop_set(self, dict sound_loop_set not None, dict player_settings):
        """
        Immediately play a sound loop set.

        Args:
            sound_loop_set: The sound_loop_set asset object to play.
            player_settings: Settings to use for playback
        """
        cdef SoundLoopSetPlayer *player
        cdef SoundLoopLayerSettings *layer
        cdef bint player_already_playing = False

        self.log.debug("play_sound_loop_set - Preparing sound_loop_set '%s' for playback.", sound_loop_set)

        if player_settings is None:
            player_settings = dict()

        # Determine settings (override sound loop set with player settings)
        player_settings.setdefault('fade_in', sound_loop_set['fade_in'])
        player_settings.setdefault('fade_out', sound_loop_set['fade_out'])
        player_settings.setdefault('events_when_played', sound_loop_set['events_when_played'])
        player_settings.setdefault('events_when_stopped', sound_loop_set['events_when_stopped'])
        player_settings.setdefault('events_when_looping', sound_loop_set['events_when_looping'])
        player_settings.setdefault('mode_end_action', sound_loop_set['mode_end_action'])
        player_settings.setdefault('queue', True)
        player_settings.setdefault('synchronize', False)

        SDL_LockAudio()

        # Determine current track player status so we can determine what action(s) should be
        # taken to play the requested loop set.  There should never be a situation where the
        # current player is idle while the next one is playing.
        if self.type_state.current.status == player_idle:

            # The current player is idle.  This is the simplest case as the queue and
            # synchronize settings can be ignored as we simply start playing the requested
            # loop set immediately on the current player.
            player = self.type_state.current
            player_already_playing = False

        elif self.type_state.next.status == player_idle:

            # The current player is busy playing a loop set.  In this case the queue and
            # synchronize settings are important and dictate how the requested loop set
            # will be played.
            player = self.type_state.next
            player_already_playing = True

        else:
            # TODO: Handle case when both players are busy (i.e. during a cross-fade)
            self.log.info("Unable to play sound - both sound loop players are currently busy.")
            SDL_UnlockAudio()
            return

        # Calculate fading (done at control rate; need to calculate the number of steps over which to fade in/out)
        player.master_sound_layer.fade_in_steps = player_settings['fade_in'] * self.state.callback_data.seconds_to_bytes_factor // self.state.callback_data.bytes_per_control_point
        player.master_sound_layer.fade_out_steps = player_settings['fade_out'] * self.state.callback_data.seconds_to_bytes_factor // self.state.callback_data.bytes_per_control_point
        player.master_sound_layer.fade_steps_remaining = player.master_sound_layer.fade_in_steps

        if player_already_playing:

            # Determine if playing immediately or queuing until next loop
            if player_settings['queue']:
                player.status = player_pending
                player.sample_pos = 0

            else:
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

            player.sample_pos = 0

        master_layer_settings = {
            "sound": sound_loop_set['sound'],
            "volume": sound_loop_set['volume'],
            "initial_state": "play"
        }
        self._apply_layer_settings(&player.master_sound_layer, master_layer_settings)

        # Determine master sound length
        if player.master_sound_layer.sound != NULL:
            player.length = <Uint32>player.master_sound_layer.sound.data.memory.size

            # Adjust sample position to ensure it is within the sample
            while player.sample_pos >= player.length:
                player.sample_pos -= player.length
        else:
            player.length = 0
            player.sample_pos = 0

        # Setup sound loop set layers
        self._reset_player_layers(player)

        for layer_settings in sound_loop_set['layers']:
            layer = _create_sound_loop_layer_settings()
            self._apply_layer_settings(layer, layer_settings)

            # Layer fading is only set by events using the sound_loop_player
            layer.fade_in_steps = 0
            layer.fade_out_steps = 0
            layer.fade_steps_remaining = 0

            # Append layer
            player.layers = g_slist_append(player.layers, layer)

        SDL_UnlockAudio()

    cdef _apply_layer_settings(self, SoundLoopLayerSettings *layer, dict layer_settings):
        cdef SoundFile sound_container

        if 'initial_state' not in layer_settings or layer_settings['initial_state'] == 'play':
            layer.status = layer_playing
        else:
            layer.status = layer_stopped

        # Set layer sound
        sound = self.mc.sounds[layer_settings['sound']]

        # TODO: What to do when sound is not loaded?
        # TODO: Perhaps load sounds and delay play until loaded?

        sound_container = sound.container
        layer.sound = cython.address(sound_container.sample)
        layer.sound_id = sound.id

        # By default, all layers will continue to loop when played
        layer.looping = True

        # Layer volume (use layer settings or sound setting if None)
        if layer_settings['volume']:
            layer.volume = <Uint8>(layer_settings['volume'] * SDL_MIX_MAXVOLUME)
        else:
            layer.volume = <Uint8>(sound.volume * SDL_MIX_MAXVOLUME)

        # Markers (copy from source sound)
        layer.markers = NULL
        layer.marker_count = 0
        # TODO: implement sound marker support
        '''
        layer.marker_count = sound.marker_count

        if layer.marker_count > 0:
            layer.markers = g_array_new(False, False, sizeof(guint))
            g_array_set_size(layer.markers, sound.marker_count)
            for index in range(sound.marker_count):
                g_array_insert_val_uint(layer.markers,
                                        index,
                                        <guint>(sound.markers[index]['time'] * self.state.callback_data.seconds_to_bytes_factor))

        '''

    def stop_current_sound_loop_set(self, fade_out=None):
        """
        Stops the currently playing sound loop set.
        Args:
            fade_out: The number of seconds over which to fade out the currently playing
                      sound loop set before stopping.
        """
        SDL_LockAudio()

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

        SDL_UnlockAudio()

    def stop_looping_current_sound_loop_set(self):
        """
        Stops the currently playing sound loop set from continuing to loop (it will stop
        after the current loop iteration).
        """
        SDL_LockAudio()

        if self.type_state.current.status not in (player_playing, player_fading_in, player_fading_out):
            self.log.info("Unable to stop looping sound loop set - no sound loop set is currently playing.")
            SDL_UnlockAudio()
            return

        self.type_state.current.master_sound_layer.looping = False

        SDL_UnlockAudio()

    def play_layer(self, int layer, float fade_in=0.0, bint queue=True, volume=None):
        """
        Plays the specified layer number in the currently playing sound loop set.

        Args:
            layer: The layer number to play (1-based array position).
            fade_in: The number of seconds over which to fade in the layer.
            queue: Flag indicating whether the layer should be played immediately (False)
                   or queued until the next loop of the master layer loop (True).
            volume: The layer volume (overrides sound loop set setting if not None)
        """
        cdef SoundLoopLayerSettings *layer_settings

        if layer < 1:
            self.log.warning("Illegal layer value in call to play_layer (must be > 0).")
            return

        SDL_LockAudio()

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

        if queue:
            layer_settings.status = layer_queued
        elif layer_settings.fade_in_steps > 0:
            layer_settings.status = layer_fading_in
        else:
            layer_settings.status = layer_playing

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
        cdef TrackSoundLoopState *live_loop_track
        cdef bint first_layer = True
        cdef bint switch_players = False
        cdef bint reset_track_buffer_pos = True
        cdef SoundLoopSetPlayer *player

        #fprintf(callback_data.c_log_file, "TrackSoundLoop.mix_playing_sounds ###########################\r\n")
        #fflush(callback_data.c_log_file)

        if track == NULL or track.type_state == NULL:
            return

        live_loop_track = <TrackSoundLoopState*>track.type_state

        # Setup local variables
        cdef Uint32 track_buffer_pos

        # If the current player is idle, the track is not active so there is nothing to do
        if live_loop_track.current == NULL or live_loop_track.current.status == player_idle:
            return

        # Set flag indicating there is at least some activity on the track (it is active)
        track.active = True

        # Process the current loop player
        track_buffer_pos = 0
        while track_buffer_pos < buffer_length and live_loop_track.current.status \
                in (player_playing, player_fading_in, player_fading_out):

            #fprintf(callback_data.c_log_file, "TrackSoundLoop.mix_playing_sounds - current track_buffer_pos = %d\r\n", track_buffer_pos)
            #fflush(callback_data.c_log_file)

            track_buffer_pos = get_player_sound_samples(track, live_loop_track.current,
                                                        buffer_length, track_buffer_pos,
                                                        callback_data)

            # Check if we have reached the end of the sound loop.
            if live_loop_track.current.sample_pos >= live_loop_track.current.length:
                # End of sound loop reached, determine if sound loop set should end or continue looping
                # If the current player is fading out, we need to wait for it to finish before moving
                # on to the next player
                if not live_loop_track.current.master_sound_layer.looping or (
                        live_loop_track.current.status == player_playing and live_loop_track.next.status == player_pending):

                    live_loop_track.current.status = player_idle
                    reset_track_buffer_pos = False

                    # TODO: Send stopped notification

                    switch_players = True
                    if live_loop_track.next.status == player_pending:
                        live_loop_track.next.status = player_playing
                else:
                    # TODO: send looping notification
                    #send_sound_looping_notification(0, sound.sound_id, 0, track)
                    live_loop_track.current.sample_pos = 0

        if reset_track_buffer_pos:
            track_buffer_pos = 0

        # Now process the next player
        while track_buffer_pos < buffer_length and live_loop_track.next.status \
                in (player_playing, player_fading_in, player_fading_out):

            #fprintf(callback_data.c_log_file, "TrackSoundLoop.mix_playing_sounds - next track_buffer_pos = %d\r\n", track_buffer_pos)
            #fflush(callback_data.c_log_file)

            track_buffer_pos = get_player_sound_samples(track, live_loop_track.next,
                                                        buffer_length, track_buffer_pos,
                                                        callback_data)

            # Check if we have reached the end of the sound loop.
            if live_loop_track.next.sample_pos >= live_loop_track.next.length:
                # End of sound loop reached, the next player will always loop
                # TODO: send looping notification
                live_loop_track.next.sample_pos = 0

        # Switch current and next players (if necessary)
        if switch_players:
            #fprintf(callback_data.c_log_file, "TrackSoundLoop.mix_playing_sounds - switching players\r\n")
            #fflush(callback_data.c_log_file)

            player = live_loop_track.current
            live_loop_track.current = live_loop_track.next
            live_loop_track.next = player

            #fprintf(callback_data.c_log_file, "TrackSoundLoop.mix_playing_sounds - finished\r\n")
            #fflush(callback_data.c_log_file)

cdef Uint32 get_player_sound_samples(TrackState *track, SoundLoopSetPlayer *player,
                                     Uint32 buffer_length, Uint32 track_buffer_pos,
                                     AudioCallbackData *callback_data) nogil:
    """
    
    Args:
        track: 
        player: 
        buffer_length: 
        track_buffer_pos: 
        callback_data: 

    Returns:
        The updated track buffer position.
    """

    cdef SoundLoopLayerSettings *layer
    cdef GSList *layer_iterator
    cdef Uint8 player_volume, layer_volume
    cdef Uint32 layer_sample_pos, layer_bytes_remaining, layer_chunk_bytes, current_chunk_bytes
    cdef Uint32 layer_track_buffer_pos_offset
    cdef bint end_of_loop = False
    cdef Uint32 buffer_bytes_remaining = buffer_length - track_buffer_pos

    # Loop over the output buffer
    while buffer_bytes_remaining > 0:

        #fprintf(callback_data.c_log_file, "TrackSoundLoop.get_player_sound_samples buffer_bytes_remaining = %d\r\n", buffer_bytes_remaining)
        #fflush(callback_data.c_log_file)

        # Mix current player into track buffer.  Processing is done at control rate during player
        # fading and using full buffer when no fading is occurring.

        # Calculate volume of chunk (handle fading)
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

        #fprintf(callback_data.c_log_file, "TrackSoundLoop.get_player_sound_samples current_chunk_bytes = %d\r\n", current_chunk_bytes)
        #fflush(callback_data.c_log_file)

        # Get master layer
        if player.status == player_idle:
            return buffer_length

        # The master layer does not support fading so we do not need to copy samples
        # at control rate here.
        SDL_MixAudioFormat(track.buffer + track_buffer_pos,
                           <Uint8*>player.master_sound_layer.sound.data.memory.data + player.sample_pos,
                           track.callback_data.format,
                           current_chunk_bytes,
                           player_volume * player.master_sound_layer.volume // SDL_MIX_MAXVOLUME)

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

                    layer_track_buffer_pos_offset += layer_chunk_bytes
                    layer_sample_pos += layer_chunk_bytes
                    layer_bytes_remaining -= layer_chunk_bytes

            # Move to next layer
            layer_iterator = layer_iterator.next

        # Advance buffer pointers
        player.sample_pos += current_chunk_bytes
        track_buffer_pos += current_chunk_bytes
        buffer_bytes_remaining -= current_chunk_bytes

        # Stop looping and generating samples if we have reached the end of the loop or
        # the player is now idle (due to reaching end of a fade out)
        #fprintf(callback_data.c_log_file, "TrackSoundLoop.get_player_sound_samples player.sample_pos = %d, player.length = %d\r\n", player.sample_pos, player.length)
        #fflush(callback_data.c_log_file)
        if player.status == player_idle or player.sample_pos >= player.length:
            #fprintf(callback_data.c_log_file, "TrackSoundLoop.get_player_sound_samples player has stopped or reached end of sound\r\n")
            #fflush(callback_data.c_log_file)
            break

    return track_buffer_pos


cdef inline SoundLoopLayerSettings *_create_sound_loop_layer_settings() nogil:
    """
    Creates a new sound loop layer settings struct.
    :return: A pointer to the new settings struct.
    """
    return <SoundLoopLayerSettings*>g_slice_alloc0(sizeof(SoundLoopLayerSettings))


