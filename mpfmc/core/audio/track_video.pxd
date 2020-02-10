from mpfmc.core.audio.sdl2 cimport *
from mpfmc.core.audio.gstreamer cimport *
from mpfmc.core.audio.track cimport *
from mpfmc.core.audio.track_standard cimport *
from mpfmc.core.audio.sound_file cimport *
from mpfmc.core.audio.notification_message cimport *


# ---------------------------------------------------------------------------
#    Video Track types
# ---------------------------------------------------------------------------

ctypedef struct VideoSettings:
    SampleStream *stream
    Uint8 volume
    Uint32 sample_pos
    FadingStatus fading_status
    Uint32 fade_in_steps
    Uint32 fade_out_steps
    Uint32 fade_steps_remaining
    Uint8 marker_count
    GArray *markers
    Uint32 about_to_finish_marker
    bint video_has_ducking
    DuckingSettings ducking_settings
    DuckingStage ducking_stage
    GArray *ducking_control_points

ctypedef struct TrackVideoState:
    # State variables for TrackVideo tracks
    GSList *videos


# ---------------------------------------------------------------------------
#    TrackVideo class
# ---------------------------------------------------------------------------
cdef class TrackVideo(Track):

    cdef dict _active_videos_by_name

    # Track state needs to be stored in a C struct in order for them to be accessible in
    # the SDL callback functions without the GIL (for performance reasons).
    # The TrackVideoState struct is allocated during construction and freed during
    # destruction.
    cdef TrackVideoState *type_state

    cdef process_notification_message(self, NotificationMessageContainer *notification_message)

    @staticmethod
    cdef void mix_playing_sounds(TrackState *track, Uint32 buffer_length, AudioCallbackData *callback_data) nogil

cdef inline VideoSettings *_create_video_settings() nogil
