from mpfmc.core.audio.sdl2 cimport *
from mpfmc.core.audio.gstreamer cimport *
from mpfmc.core.audio.sound_file cimport *
from mpfmc.core.audio.track cimport *
from mpfmc.core.audio.notification_message cimport *
from mpfmc.core.audio.track_standard cimport *


# ---------------------------------------------------------------------------
#    Playlist Track types
# ---------------------------------------------------------------------------

ctypedef struct TrackPlaylistState:
    # State variables for TrackPlaylist tracks
    float crossfade_time
    int sound_player_count
    SoundPlayer *sound_players


# ---------------------------------------------------------------------------
#    TrackPlaylist class
# ---------------------------------------------------------------------------
cdef class TrackPlaylist(Track):

    cdef dict _playing_sound_instances_by_id
    cdef dict _playlist_instances_by_sound_instance_id

    # Track state needs to be stored in a C struct in order for them to be accessible in
    # the SDL callback functions without the GIL (for performance reasons).
    # The TrackPlaylist struct is allocated during construction and freed during
    # destruction.
    cdef TrackPlaylistState *type_state

    @staticmethod
    cdef void mix_playing_sounds(TrackState *track, Uint32 buffer_length, AudioCallbackData *callback_data) nogil

