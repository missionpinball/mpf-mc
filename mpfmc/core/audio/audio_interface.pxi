
cdef extern from "Python.h":
    void PyEval_InitThreads()

cdef extern from "SDL.h" nogil:

    ctypedef unsigned char Uint8
    ctypedef signed char Sint8
    ctypedef unsigned long Uint32
    ctypedef signed long Sint32
    ctypedef unsigned long long Uint64
    ctypedef signed long long Sint64
    ctypedef signed short Sint16
    ctypedef unsigned short Uint16

    cdef int SDL_INIT_AUDIO
    cdef int AUDIO_S16SYS

    struct SDL_AudioSpec:
        int freq
        Uint16 format
        Uint8 channels
        Uint8 silence
        Uint16 samples
        Uint16 padding
        Uint32 size
        void (*callback)(void *userdata, Uint8 *stream, int len)
        void *userdata

    struct SDL_mutex:
        pass

    struct SDL_Thread:
        pass

    SDL_mutex *SDL_CreateMutex()
    void SDL_DestroyMutex(SDL_mutex *)
    int SDL_LockMutex(SDL_mutex *)
    int SDL_UnlockMutex(SDL_mutex *)

    struct SDL_cond:
        pass

    SDL_cond *SDL_CreateCond()
    void SDL_DestroyCond(SDL_cond *)
    int SDL_CondSignal(SDL_cond *)
    int SDL_CondWait(SDL_cond *, SDL_mutex *)

    struct SDL_Thread:
        pass

    ctypedef int (*SDLCALL)(void *)
    SDL_Thread *SDL_CreateThread(SDLCALL, void *data)
    void SDL_WaitThread(SDL_Thread *thread, int *status)
    Uint32 SDL_ThreadID()

    char *SDL_GetError()

    struct SDL_UserEvent:
        Uint8 type
        int code
        void *data1
        void *data2

    union SDL_Event:
        Uint8 type

    int SDL_PushEvent(SDL_Event *event)
    void SDL_Delay(int)
    int SDL_Init(int)
    void SDL_Quit()
    void SDL_LockAudio()
    void SDL_UnlockAudio()

    ctypedef Uint16 SDL_AudioFormat

    void SDL_MixAudio(Uint8 *dst, const Uint8 *src, Uint32 len, int volume)
    void SDL_MixAudioFormat(Uint8 *dst, const Uint8 *src, SDL_AudioFormat format,
                                                Uint32 len, int volume)

    Uint32 SDL_GetTicks()

    struct SDL_version:
        Uint8 major
        Uint8 minor
        Uint8 patch

    void SDL_GetVersion(SDL_version *ver)

cdef extern from "SDL_mixer.h" nogil:
    struct Mix_Chunk:
        int allocated
        Uint8 *abuf
        Uint32 alen
        Uint8 volume

    cdef int MIX_MAX_VOLUME

    cdef struct SDL_RWops:
        long (* seek) (SDL_RWops * context, long offset,int whence)
        size_t(* read) ( SDL_RWops * context, void *ptr, size_t size, size_t maxnum)
        size_t(* write) (SDL_RWops * context, void *ptr,size_t size, size_t num)
        int (* close) (SDL_RWops * context)

    cdef enum MIX_InitFlags:
        MIX_INIT_FLAC        = 0x00000001,
        MIX_INIT_MP3         = 0x00000008,
        MIX_INIT_OGG         = 0x00000010


    SDL_RWops *SDL_RWFromFile(const char *file, const char *mode)

    int Mix_Init(int)
    void Mix_Quit()
    int Mix_OpenAudio(int frequency, Uint16 format, int channels, int chunksize)
    void Mix_CloseAudio()
    char *Mix_GetError()
    const SDL_version *Mix_Linked_Version()
    Mix_Chunk *Mix_QuickLoad_RAW(Uint8 *mem, Uint32 l)
    Mix_Chunk *Mix_LoadWAV_RW(SDL_RWops *src, int freesrc)
    Mix_Chunk *Mix_LoadWAV(char *file)
    void Mix_FreeChunk(Mix_Chunk *chunk)
    int Mix_QuerySpec(int *frequency, Uint16 *format,int *channels)
    void Mix_HookMusic(void (*mix_func)(void *, Uint8 *, int), void *arg)
    void *Mix_GetMusicHookData()


# ---------------------------------------------------------------------------
#    Helper structures
# ---------------------------------------------------------------------------

# The following declarations are not from SDL/SDL_Mixer, but are application-
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


# ---------------------------------------------------------------------------
#    Settings
# ---------------------------------------------------------------------------

# The number of control points per audio buffer (sets control rate for ducking)
DEF CONTROL_POINTS_PER_BUFFER = 8

# The maximum number of markers that can be specified for a single sound
DEF MAX_MARKERS = 8


# ---------------------------------------------------------------------------
#    Track-related types
# ---------------------------------------------------------------------------

cdef enum TrackType:
    # Enumeration of the possible track types
    track_type_none = 0
    track_type_standard = 1
    track_type_playlist = 2
    track_type_live_loop = 3

ctypedef struct TrackState:
    # Common track state variables (for all track types)
    TrackType type
    void* type_state
    bint active
    int number
    Uint8 volume
    int buffer_size
    void *buffer
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

ctypedef struct SoundSettings:
    Mix_Chunk *chunk
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
    int marker_count
    Uint32 markers[MAX_MARKERS]
    bint sound_has_ducking
    DuckingSettings ducking_settings
    DuckingStage ducking_stage
    Uint8 ducking_control_points[CONTROL_POINTS_PER_BUFFER]

ctypedef struct SoundPlayer:
    # The SoundPlayer keeps track of the current sample position in the source audio
    # chunk and is also keeps track of variables for sound looping and determining when the
    # sound has finished playing.
    SoundPlayerStatus status
    SoundSettings current
    SoundSettings next
    int track_num
    int player


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
    int sample_rate
    int audio_channels
    Uint32 buffer_size
    Uint8 master_volume
    int track_count
    TrackState **tracks
    RequestMessageContainer **request_messages
    NotificationMessageContainer **notification_messages
    SDL_mutex *mutex
    FILE *c_log_file


# ---------------------------------------------------------------------------
#    Request Message types
# ---------------------------------------------------------------------------

cdef enum RequestMessage:
    request_not_in_use = 0               # Message is not in use and is available
    request_sound_play = 1               # Request to play a sound
    request_sound_replace = 2            # Request to play a sound that replaces a sound in progress
    request_sound_stop = 3               # Request to stop a sound that is playing
    request_sound_stop_looping = 4       # Request to stop looping a sound that is playing


ctypedef struct RequestMessageDataPlaySound:
    Mix_Chunk *chunk
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

ctypedef union RequestMessageData:
    RequestMessageDataPlaySound play
    RequestMessageDataStopSound stop

ctypedef struct RequestMessageContainer:
    RequestMessage message
    long sound_id
    long sound_instance_id
    int track
    int player
    Uint32 time
    RequestMessageData data


# ---------------------------------------------------------------------------
#    Notification Message types
# ---------------------------------------------------------------------------

cdef enum NotificationMessage:
    notification_not_in_use = 0               # Message is not in use and is available
    notification_sound_started = 1            # Notification that a sound has started playing
    notification_sound_stopped = 2            # Notification that a sound has stopped
    notification_sound_looping = 3            # Notification that a sound is looping back to the beginning
    notification_sound_marker = 4             # Notification that a sound marker has been reached
    notification_player_idle = 5              # Notification that a player is now idle and ready to play another sound

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
    int track
    int player
    Uint32 time
    NotificationMessageData data
