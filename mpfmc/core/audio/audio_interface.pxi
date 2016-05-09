
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
    void Mix_Pause(int channel)
    void Mix_Resume(int channel)
    void Mix_CloseAudio()
    int Mix_Playing(int channel)
    int Mix_Paused(int channel)
    int Mix_PlayChannel(int channel, Mix_Chunk *chunk, int loops)
    int Mix_HaltChannel(int channel)
    int Mix_FadeInChannel(int channel, Mix_Chunk *chunk, int loops, int ms)
    int  Mix_FadeOutChannel(int channel, int ms)
    char *Mix_GetError()
    const SDL_version *Mix_Linked_Version()
    ctypedef void (*Mix_EffectFunc_t)(int, void *, int, void *)
    ctypedef void (*Mix_EffectDone_t)(int, void *)
    int Mix_RegisterEffect(int chan, Mix_EffectFunc_t f, Mix_EffectDone_t d, void * arg)
    int Mix_UnregisterAllEffects(int chan)
    int Mix_AllocateChannels(int numchans)
    Mix_Chunk *Mix_QuickLoad_RAW(Uint8 *mem, Uint32 l)
    Mix_Chunk *Mix_LoadWAV_RW(SDL_RWops *src, int freesrc)
    Mix_Chunk *Mix_LoadWAV(char *file)
    void Mix_FreeChunk(Mix_Chunk *chunk)
    int Mix_QuerySpec(int *frequency, Uint16 *format,int *channels)
    int Mix_Volume(int chan, int volume)


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

ctypedef struct TrackAttributes:
    int number
    int max_simultaneous_sounds
    int volume
    void *buffer
    int buffer_size
    SoundPlayer *sound_players
    DuckingEnvelope **ducking_envelopes

cdef enum SoundPlayerStatus:
    # Enumeration of the possible AudioSamplePlayer status values.
    player_idle,
    player_pending,
    player_replacing,
    player_playing,
    player_finished,
    player_stopping,

ctypedef struct DuckingSettings:
    int track
    int envelope_num
    Uint32 attack_start_pos
    Uint32 attack_duration
    Uint8 attenuation_volume
    Uint32 release_start_pos
    Uint32 release_duration

ctypedef struct DuckingEnvelope:
    DuckingEnvelopeStage stage
    Uint32 stage_pos
    Uint32 stage_duration
    Uint8 stage_initial_volume
    Uint8 stage_target_volume
    Uint8 current_volume

cdef enum DuckingEnvelopeStage:
    envelope_stage_idle,
    envelope_stage_delay,
    envelope_stage_attack,
    envelope_stage_sustain,
    envelope_stage_release,
    envelope_stage_finished

ctypedef struct SoundSettings:
    Mix_Chunk *chunk
    int volume
    int loops_remaining
    int current_loop
    Uint32 start_time
    Uint32 samples_elapsed
    Uint32 sample_pos
    long sound_id
    int sound_priority
    int sound_has_ducking
    DuckingSettings ducking_settings

ctypedef struct SoundPlayer:
    # The SoundPlayer keeps track of the current sample position in the source audio
    # chunk and is also keeps track of variables for sound looping and determining when the
    # sound has finished playing.
    SoundPlayerStatus status
    SoundSettings current
    SoundSettings next

ctypedef struct AudioCallbackData:
    int sample_rate
    int audio_channels
    int master_volume
    int track_count
    TrackAttributes **tracks
    AudioMessageContainer **messages
    SDL_mutex *mutex

cdef enum AudioMessage:
    message_not_in_use,               # Message is not in use and is available
    message_sound_play,               # Request to play a sound
    message_sound_replace,            # Request to play a sound that replaces a sound in progress
    message_sound_stop,               # Request to stop a sound that is playing
    message_sound_started,            # Notification that a sound has started playing
    message_sound_stopped,            # Notification that a sound has stopped
    message_sound_marker,             # Notification that a sound marker has been reached
    message_track_ducking_start,      # Request to start ducking on a track (fade down)
    message_track_ducking_stop,       # Request to stop ducking on a track (fade up)

ctypedef struct AudioMessageDataPlaySound:
    Mix_Chunk *chunk
    int volume
    int loops

ctypedef struct AudioMessageDataStopSound:
    int track
    int player

ctypedef struct AudioMessageDataMarker:
    int id

ctypedef union AudioMessageData:
    AudioMessageDataPlaySound play
    AudioMessageDataStopSound stop
    AudioMessageDataMarker marker

ctypedef struct AudioMessageContainer:
    AudioMessage message
    long sound_id
    int track
    int player
    Uint32 time
    AudioMessageData data

