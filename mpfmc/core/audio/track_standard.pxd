from mpfmc.core.audio.sdl2 cimport *
from mpfmc.core.audio.gstreamer cimport *
from mpfmc.core.audio.sound_file cimport *
from mpfmc.core.audio.track cimport *
from mpfmc.core.audio.notification_message cimport *


# ---------------------------------------------------------------------------
#    Standard Track types
# ---------------------------------------------------------------------------

cdef enum:
    no_marker = 0xFFFFFFFF

ctypedef struct TrackStandardState:
    # State variables for TrackStandard tracks
    int sound_player_count
    SoundPlayer *sound_players

cdef enum SoundPlayerStatus:
    # Enumeration of the possible sound player status values.
    player_idle = 0
    player_pending = 1
    player_replacing = 2
    player_fading_in = 3
    player_fading_out = 4
    player_playing = 5
    player_finished = 6
    player_stopping = 7

ctypedef struct DuckingSettings:
    int track_bit_mask
    Sint32 attack_start_pos
    Sint32 attack_duration
    Uint8 attenuation_volume
    Sint32 release_start_pos
    Sint32 release_duration

cdef enum DuckingStage:
    ducking_stage_idle = 0
    ducking_stage_delay = 1
    ducking_stage_attack = 2
    ducking_stage_hold = 3
    ducking_stage_release = 4
    ducking_stage_finished = 5

cdef enum FadingStatus:
    fading_status_not_fading = 0
    fading_status_fading_in = 1
    fading_status_fading_out = 2

ctypedef struct SoundSettings:
    SoundSample *sample
    Uint8 volume
    Uint8 volume_left
    Uint8 volume_right
    int loops_remaining
    int current_loop
    Uint32 sample_pos
    Uint32 loop_start_pos
    Uint32 loop_end_pos
    Uint64 sound_id
    Uint64 sound_instance_id
    int sound_priority
    FadingStatus fading_status
    Uint32 fade_in_steps
    Uint32 fade_out_steps
    Uint32 fade_steps_remaining
    Uint8 marker_count
    GArray *markers
    Uint32 about_to_finish_marker
    bint sound_has_ducking
    DuckingSettings ducking_settings
    DuckingStage ducking_stage
    GArray *ducking_control_points

ctypedef struct SoundPlayer:
    # The SoundPlayer keeps track of the current sample position in the source audio
    # samples and is also keeps track of variables for sound looping and determining when the
    # sound has finished playing.
    SoundPlayerStatus status
    SoundSettings current
    SoundSettings next
    int track_num
    int number


# ---------------------------------------------------------------------------
#    TrackStandard class
# ---------------------------------------------------------------------------
cdef class TrackStandard(Track):

    cdef list _sound_queue
    cdef dict _playing_instances_by_id
    cdef int _max_simultaneous_sounds

    # Track state needs to be stored in a C struct in order for them to be accessible in
    # the SDL callback functions without the GIL (for performance reasons).
    # The TrackStandardState struct is allocated during construction and freed during
    # destruction.
    cdef TrackStandardState *type_state

    cdef int _get_playing_sound_count(self, Uint64 sound_id)
    cdef list _get_playing_sound_instances(self, Uint64 sound_id)
    cdef int _get_idle_sound_player(self)
    cdef process_notification_message(self, NotificationMessageContainer *notification_message)
    cdef tuple _get_sound_player_with_lowest_priority(self)
    cdef bint _play_sound_on_sound_player(self, sound_instance, int player, bint force=?)
    cdef _set_player_sound_settings(self, SoundSettings *sound_settings, object sound_instance)
    cdef _set_player_playing(self, SoundPlayer *player, object sound_instance)
    cdef _set_player_replacing(self, SoundPlayer *player, object sound_instance)
    cdef int _get_player_playing_sound_instance(self, sound_instance)
    cdef Uint32 _fix_sample_frame_pos(self, Uint32 sample_pos, Uint8 bytes_per_sample, int channels)

    @staticmethod
    cdef void mix_playing_sounds(TrackState *track, Uint32 buffer_length, AudioCallbackData *callback_data) nogil

# ---------------------------------------------------------------------------
#    Global C functions designed to be called from the static audio callback
#    function (these functions do not use the GIL).
# ---------------------------------------------------------------------------

cdef bint get_memory_sound_samples(SoundSettings *sound, Uint32 length, Uint8 *output_buffer, int channels,
                                   Uint8 volume, TrackState *track, int player_num) nogil
cdef bint get_streaming_sound_samples(SoundSettings *sound, Uint32 length, Uint8 *output_buffer, int channels,
                                      Uint8 volume, TrackState *track, int player_num) nogil

cdef inline void end_of_sound_processing(SoundPlayer* player,
                                         TrackState *track) nogil:
    """
    Determines the action to take at the end of the sound (loop or stop) based on
    the current settings.  This function should be called when a sound processing
    loop has reached the end of the source buffer.
    Args:
        player: SoundPlayer pointer
        track: TrackState pointer for the current track
    """
    # Check if we are at the end of the source sample buffer (loop if applicable)
    if player.current.loops_remaining > 0:
        # At the end and still loops remaining, loop back to the beginning
        player.current.loops_remaining -= 1
        player.current.sample_pos = 0
        player.current.current_loop += 1
        send_sound_looping_notification(player.number,
                                 player.current.sound_id, player.current.sound_instance_id,
                                 track)

    elif player.current.loops_remaining == 0:
        # At the end and not looping, the sample has finished playing
        player.status = player_finished

    else:
        # Looping infinitely, loop back to the beginning
        player.current.sample_pos = 0
        player.current.current_loop += 1
        send_sound_looping_notification(player.number,
                                 player.current.sound_id, player.current.sound_instance_id,
                                 track)
