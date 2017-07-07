#!python
#cython: embedsignature=True, language_level=3

from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
cimport cpython.pycapsule as pycapsule
import cython
import logging
import time
from heapq import heappush, heappop, heapify

from mpfmc.core.audio.sdl2 cimport *
from mpfmc.core.audio.gstreamer cimport *
from mpfmc.core.audio.track cimport *
from mpfmc.core.audio.inline cimport lerpU8, in_out_quad
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
            player.layers = NULL
            player.sample_pos = 0
            player.fade_in_steps = 0
            player.fade_out_steps = 0
            player.fade_steps_remaining = 0
            player.synchronize_with_other_player = False

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

    def queue_sound_loop_set(self, dict sound_loop_set not None, dict player_settings):
        """
        Queue a sound loop set for playback.

        Args:
            sound_loop_set: The sound_loop_set asset object to queue.
            player_settings: Settings to use for queueing
        """
        self.log.debug("queue_sound_loop_set - Queuing sound_loop_set '%s' for playback.", sound_loop_set)

        SDL_LockAudio()

        SDL_UnlockAudio()

    def play_sound_loop_set(self, dict sound_loop_set not None, dict player_settings):
        """
        Immediately play a sound loop set.

        Args:
            sound_loop_set: The sound_loop_set asset object to play.
            player_settings: Settings to use for playback
        """
        cdef SoundLoopSetPlayer *player
        cdef SoundLoopLayerSettings *layer
        cdef bint other_player_playing = False
        cdef SoundFile sound_container

        self.log.debug("queue_sound_loop_set - Queuing sound_loop_set '%s' for playback.", sound_loop_set)

        if player_settings is None:
            player_settings = dict()

        # Determine settings (override sound loop set with player settings)
        player_settings.setdefault('fade_in', sound_loop_set['fade_in'])
        player_settings.setdefault('fade_out', sound_loop_set['fade_out'])
        player_settings.setdefault('events_when_played', sound_loop_set['events_when_played'])
        player_settings.setdefault('events_when_stopped', sound_loop_set['events_when_stopped'])
        player_settings.setdefault('events_when_looping', sound_loop_set['events_when_looping'])
        player_settings.setdefault('mode_end_action', sound_loop_set['mode_end_action'])
        player_settings.setdefault('synchronize', False)

        SDL_LockAudio()

        if self.type_state.current.status == player_idle:
            player = self.type_state.current
            other_player_playing = False
        elif self.type_state.next.status == player_idle:
            player = self.type_state.next
            other_player_playing = True
        else:
            # TODO: Handle case when both players are busy (i.e. during a cross-fade)
            self.log.warning("Unable to play sound - both sound loop players are currently busy.")
            return

        player.status = player_pending

        player.synchronize_with_other_player = player_settings['synchronize']

        # Fading (done at control rate; need to calculate the number of steps over which to fade in/out)
        player.fade_in_steps = player_settings['fade_in'] * self.state.callback_data.seconds_to_bytes_factor // self.state.callback_data.bytes_per_control_point
        player.fade_out_steps = player_settings['fade_out'] * self.state.callback_data.seconds_to_bytes_factor // self.state.callback_data.bytes_per_control_point
        player.fade_steps_remaining = player.fade_in_steps

        # Setup sound loop set layers
        self._reset_player_layers(player)

        for layer_settings in sound_loop_set['layers']:
            layer = _create_sound_loop_layer_settings()

            layer.volume = <Uint8>(layer_settings['volume'] * SDL_MIX_MAXVOLUME)

            if layer_settings['initial_state'] == 'play':
                layer.status = layer_playing
            else:
                layer.status = layer_stopped

            layer.fade_in_steps = 0
            layer.fade_out_steps = 0
            layer.fade_steps_remaining = 0

            sound = self.mc.sounds[layer_settings['sound']]

            # TODO: What to do when sound is not loaded?

            sound_container = sound.container
            layer.sound = cython.address(sound_container.sample)
            layer.sound_id = sound.id

            # Markers
            layer.markers = NULL
            layer.marker_count = sound.marker_count

            if layer.marker_count > 0:
                layer.markers = g_array_new(False, False, sizeof(guint))
                g_array_set_size(layer.markers, sound.marker_count)
                for index in range(sound.marker_count):
                    g_array_insert_val_uint(layer.markers,
                                            index,
                                            <guint>(sound.markers[index]['time'] * self.state.callback_data.seconds_to_bytes_factor))


            g_slist_append(player.layers, layer)

        SDL_UnlockAudio()

    cdef _reset_player_layers(self, SoundLoopSetPlayer *player):
        """Reset"""
        if player != NULL and player.layers != NULL:
            iterator = player.layers
            while iterator != NULL:
                layer = <SoundLoopLayerSettings*>iterator.data
                if layer.markers != NULL:
                    g_array_free(layer.markers, True)
                    layer.markers = NULL
                iterator = iterator.next

            g_slist_free(player.layers)
            player.layers = NULL


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

        if track == NULL or track.type_state == NULL:
            return

        live_loop_track = <TrackSoundLoopState*>track.type_state

        # Setup local variables

        # Process current sound loop set

            # Loop over output buffer at control rate

            # Loop over layers




        # Process next sound loop set (if necessary)


cdef inline SoundLoopLayerSettings *_create_sound_loop_layer_settings() nogil:
    """
    Creates a new sound loop layer settings struct.
    :return: A pointer to the new settings struct.
    """
    return <SoundLoopLayerSettings*>g_slice_alloc0(sizeof(SoundLoopLayerSettings))

