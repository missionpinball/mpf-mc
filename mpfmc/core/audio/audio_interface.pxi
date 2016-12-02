# ---------------------------------------------------------------------------
#    Helper structures
# ---------------------------------------------------------------------------

# The following declarations are not from SDL, but are application-
# specific data structures used in the MPF media controller audio library:

cdef struct Sample16Bytes:
    # Structure that represents two bytes of a 16-bit sample.  This is used in
    # the union below (nested structs are not permitted in Cython so it is
    # declared separately here).
    Uint8 byte0
    Uint8 byte1

cdef union Sample16Bit:
    # Union structure that represents a single 16-bit sample value.  A union is
    # utilized to make it easy to access the individual bytes in the sample.
    # This is needed since all samples are streamed as individual 8-bit (byte)
    # values.
    Sint16 value
    Sample16Bytes bytes

ctypedef struct SampleMemory:
    gpointer data
    gsize size

ctypedef struct SampleStream:
    GstElement *pipeline
    GstElement *sink
    GstSample *sample
    GstBuffer *buffer
    GstMapInfo map_info
    Uint32 map_buffer_pos
    gboolean map_contains_valid_sample_data
    gint null_buffer_count


# ---------------------------------------------------------------------------
#    Settings
# ---------------------------------------------------------------------------

# The number of control points per audio buffer (sets control rate for ducking)
DEF CONTROL_POINTS_PER_BUFFER = 8

# The maximum number of markers that can be specified for a single sound
DEF MAX_MARKERS = 8

# The maximum number of consecutive null buffers to receive while streaming before
# terminating the sound (will cause drop outs)
DEF CONSECUTIVE_NULL_STREAMING_BUFFER_LIMIT = 2


# ---------------------------------------------------------------------------
#    Track-related types
# ---------------------------------------------------------------------------

cdef enum TrackType:
    # Enumeration of the possible track types
    track_type_none = 0
    track_type_standard = 1
    track_type_playlist = 2
    track_type_live_loop = 3

cdef enum TrackStatus:
    track_status_stopped = 0
    track_status_stopping = 1
    track_status_playing = 2
    track_status_pausing = 3
    track_status_paused = 4

ctypedef struct TrackState:
    # Common track state variables (for all track types)
    AudioCallbackData *callback_data
    TrackType type
    void* type_state
    TrackStatus status
    bint active
    int number
    Uint8 volume
    Uint8 fade_volume_start
    Uint8 fade_volume_target
    Uint8 fade_volume_current
    Uint32 fade_steps
    Uint32 fade_steps_remaining
    int buffer_size
    Uint8 *buffer
    GSList *notification_messages
    bint ducking_is_active
    Uint8 ducking_control_points[CONTROL_POINTS_PER_BUFFER]


# ---------------------------------------------------------------------------
#    Standard Track types
# ---------------------------------------------------------------------------

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

cdef enum SoundType:
    sound_type_memory = 0
    sound_type_streaming = 1

ctypedef union SoundSampleData:
    SampleMemory *memory
    SampleStream *stream

ctypedef struct SoundSample:
    SoundType type
    SoundSampleData data
    double duration

ctypedef struct SoundSettings:
    SoundSample *sample
    Uint8 volume
    int loops_remaining
    int current_loop
    Uint32 sample_pos
    long sound_id
    long sound_instance_id
    int sound_priority
    FadingStatus fading_status
    Uint32 fade_in_steps
    Uint32 fade_out_steps
    Uint32 fade_steps_remaining
    Uint8 marker_count
    Uint32 markers[MAX_MARKERS]
    Uint32 almost_finished_marker
    bint sound_has_ducking
    DuckingSettings ducking_settings
    DuckingStage ducking_stage
    Uint8 ducking_control_points[CONTROL_POINTS_PER_BUFFER]

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
#    Playlist Track types
# ---------------------------------------------------------------------------

ctypedef struct TrackPlaylistState:
    # State variables for TrackPlaylist tracks
    SoundPlayer *player_one
    SoundPlayer *player_two
    float crossfade_seconds


# ---------------------------------------------------------------------------
#    Live Loop Track types
# ---------------------------------------------------------------------------

ctypedef struct TrackLiveLoopState:
    # State variables for TrackLiveLoop tracks
    SoundPlayer *master_sound_player
    int slave_sound_player_count
    SoundPlayer *slave_sound_players


# ---------------------------------------------------------------------------
#    Audio Callback Data type
# ---------------------------------------------------------------------------

ctypedef struct AudioCallbackData:
    # A pointer to this struct is passed to the main audio callback function and
    # is the only way data is made available to the main audio thread.  Must not
    # contain any Python objects.
    SDL_AudioDeviceID device_id
    SDL_AudioFormat format
    Uint16 sample_rate
    Uint8 channels
    Uint16 buffer_samples
    Uint32 buffer_size
    Uint16 bytes_per_control_point
    Uint8 bytes_per_sample
    double seconds_to_bytes_factor
    Uint8 quick_fade_steps
    Uint8 master_volume
    Uint8 silence
    Uint8 track_count
    TrackState **tracks
    FILE *c_log_file


# ---------------------------------------------------------------------------
#    Request Message types
# ---------------------------------------------------------------------------

cdef enum RequestMessage:
    request_sound_play = 1                # Request to play a sound
    request_sound_play_when_finished = 2  # Request to play a sound when the current one is finished
    request_sound_replace = 3             # Request to play a sound that replaces a sound in progress
    request_sound_stop = 4                # Request to stop a sound that is playing
    request_sound_stop_looping = 5        # Request to stop looping a sound that is playing


ctypedef struct RequestMessageDataPlaySound:
    SoundSample *sample
    Uint8 volume
    int loops
    int priority
    Uint32 start_at_position
    Uint32 fade_in_duration
    Uint32 fade_out_duration
    int marker_count
    Uint32 markers[MAX_MARKERS]
    bint sound_has_ducking
    DuckingSettings ducking_settings

ctypedef struct RequestMessageDataStopSound:
    Uint32 fade_out_duration
    Uint32 ducking_release_duration

ctypedef union RequestMessageData:
    RequestMessageDataPlaySound play
    RequestMessageDataStopSound stop

ctypedef struct RequestMessageContainer:
    RequestMessage message
    long sound_id
    long sound_instance_id
    int player
    RequestMessageData data


# ---------------------------------------------------------------------------
#    Notification Message types
# ---------------------------------------------------------------------------

cdef enum NotificationMessage:
    notification_sound_started = 1            # Notification that a sound has started playing
    notification_sound_stopped = 2            # Notification that a sound has stopped
    notification_sound_looping = 3            # Notification that a sound is looping back to the beginning
    notification_sound_marker = 4             # Notification that a sound marker has been reached
    notification_sound_about_to_finish = 5    # Notification that a sound is about to finish playing
    notification_player_idle = 10             # Notification that a player is now idle and ready to play another sound
    notification_track_stopped = 0            # Notification that the track has stopped
    notification_track_paused = 21            # Notification that the track has been paused

ctypedef struct NotificationMessageDataLooping:
    int loop_count
    int loops_remaining

ctypedef struct NotificationMessageDataMarker:
    int id

ctypedef union NotificationMessageData:
    NotificationMessageDataLooping looping
    NotificationMessageDataMarker marker

ctypedef struct NotificationMessageContainer:
    NotificationMessage message
    long sound_id
    long sound_instance_id
    int player
    NotificationMessageData data
