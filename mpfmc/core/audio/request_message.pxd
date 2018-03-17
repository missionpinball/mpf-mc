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
    GArray *markers
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
    Uint64 sound_id
    Uint64 sound_instance_id
    int player
    RequestMessageData data


