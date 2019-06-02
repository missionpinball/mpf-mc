from mpfmc.core.audio.sdl2 cimport *
from mpfmc.core.audio.gstreamer cimport *
from mpfmc.core.audio.sound_file cimport *
from mpfmc.core.audio.track cimport *
from mpfmc.core.audio.notification_message cimport *


# ---------------------------------------------------------------------------
#    Sound Loop Track types
# ---------------------------------------------------------------------------
cdef enum:
    do_not_stop_loop = 0xFFFFFFFF

cdef enum LayerStatus:
    layer_stopped = 0
    layer_queued = 1
    layer_playing = 2
    layer_fading_in = 3
    layer_fading_out = 4

ctypedef struct SoundLoopLayerSettings:
    LayerStatus status
    SoundSample *sound
    Uint8 volume
    long sound_loop_set_id
    Uint64 sound_id
    Uint32 fade_in_steps
    Uint32 fade_out_steps
    Uint32 fade_steps_remaining
    bint looping
    Uint8 marker_count
    GArray *markers

cdef enum SoundLoopSetPlayerStatus:
    # Enumeration of the possible sound loop set player status values.
    player_idle = 0
    player_delayed = 1
    player_fading_in = 2
    player_fading_out = 3
    player_playing = 4

ctypedef struct SoundLoopSetPlayer:
    SoundLoopSetPlayerStatus status
    Uint32 length
    SoundLoopLayerSettings master_sound_layer
    GSList *layers     # An array of SoundLoopLayerSettings objects
    Uint32 sample_pos
    Uint32 stop_loop_samples_remaining
    Uint32 start_delay_samples_remaining
    float tempo

ctypedef struct TrackSoundLoopState:
    # State variables for TrackSoundLoop tracks
    GSList *players
    SoundLoopSetPlayer *current


# ---------------------------------------------------------------------------
#    TrackSoundLoop class
# ---------------------------------------------------------------------------
cdef class TrackSoundLoop(Track):

    # Track state needs to be stored in a C struct in order for them to be accessible in
    # the SDL callback functions without the GIL (for performance reasons).
    # The TrackSoundLoopState struct is allocated during construction and freed during
    # destruction.
    cdef TrackSoundLoopState *type_state
    cdef long _sound_loop_set_counter
    cdef dict _active_sound_loop_sets

    cdef process_notification_message(self, NotificationMessageContainer *notification_message)

    cdef _apply_layer_settings(self, SoundLoopLayerSettings *layer, dict layer_settings)
    cdef _initialize_player(self, SoundLoopSetPlayer *player)
    cdef _delete_player(self, SoundLoopSetPlayer *player)
    cdef _delete_player_layers(self, SoundLoopSetPlayer *player)
    cdef _cancel_all_delayed_players(self)
    cdef _fade_out_all_players(self, Uint32 fade_steps)
    cdef inline Uint32 _round_sample_pos_up_to_interval(self, Uint32 sample_pos, Uint32 interval, int bytes_per_sample_frame)

    @staticmethod
    cdef void mix_playing_sounds(TrackState *track, Uint32 buffer_length, AudioCallbackData *callback_data) nogil


cdef SoundLoopLayerSettings *_create_sound_loop_layer_settings() nogil
