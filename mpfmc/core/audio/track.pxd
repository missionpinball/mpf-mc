from mpfmc.core.audio.sdl2 cimport *
from mpfmc.core.audio.gstreamer cimport *


# ---------------------------------------------------------------------------
#    Track-related types
# ---------------------------------------------------------------------------

# The number of control points per audio buffer (sets control rate for ducking)
cdef enum:
    CONTROL_POINTS_PER_BUFFER = 8

cdef enum:
    MAX_SIMULTANEOUS_SOUNDS_DEFAULT = 8

cdef enum:
    MAX_SIMULTANEOUS_SOUNDS_LIMIT = 32


cdef enum TrackStatus:
    track_status_stopped = 0
    track_status_stopping = 1
    track_status_playing = 2
    track_status_pausing = 3
    track_status_paused = 4

ctypedef struct TrackState:
    # Common track state variables (for all track types)
    AudioCallbackData *callback_data
    void (*mix_callback_function)(TrackState *track, Uint32 buffer_length, AudioCallbackData *callback_data) nogil
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
    GArray* ducking_control_points


# ---------------------------------------------------------------------------
#    Track base class
# ---------------------------------------------------------------------------
cdef class Track:

    cdef str _name
    cdef int _number
    cdef list _events_when_stopped
    cdef list _events_when_played
    cdef list _events_when_paused
    cdef object mc
    cdef SDL_AudioDeviceID device_id
    cdef object log

    # Track attributes need to be stored in a C struct in order for them to be accessible in
    # the SDL callback functions without the GIL (for performance reasons).  The TrackState
    # struct is allocated during construction and freed during destruction.
    cdef TrackState *state

    cdef TrackState *get_state(self)

    # ---------------------------------------------------------------------------
    #    Static C functions designed to be called from the static audio callback
    #    function (these functions do not use the GIL).
    # ---------------------------------------------------------------------------
    @staticmethod
    cdef void mix_track_to_output(TrackState *track, AudioCallbackData* callback_data,
                                  Uint8 *output_buffer, Uint32 buffer_length) nogil

    @staticmethod
    cdef void mix_audio(Uint8* output_buffer, const Uint8* input_buffer, Uint32 buffer_length, int volume) nogil

    @staticmethod
    cdef void mix_audio_stereo(Uint8* output_buffer, const Uint8* input_buffer, Uint32 buffer_length,
                               int volume_left, int volume_right) nogil

    @staticmethod
    cdef void apply_volume(Uint8* output_buffer, const Uint8* input_buffer, Uint32 buffer_length, int volume) nogil

    @staticmethod
    cdef void apply_volume_stereo(Uint8* output_buffer, const Uint8* input_buffer, Uint32 buffer_length,
                                  int volume_left, int volume_right) nogil
