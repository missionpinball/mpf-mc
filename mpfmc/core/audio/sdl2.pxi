# ---------------------------------------------------------------------------
#    Definitions from SDL2 and SDL_Mixer libraries
# ---------------------------------------------------------------------------

cdef extern from "Python.h":
    void PyEval_InitThreads()

cdef extern from "stdio.h" nogil:
    cdef struct __sFILE:
        pass
    ctypedef __sFILE FILE

# ---------------------------------------------------------------------------
#    SDL2
# ---------------------------------------------------------------------------
cdef extern from "SDL.h" nogil:

    ctypedef unsigned char Uint8
    ctypedef signed char Sint8
    ctypedef unsigned long Uint32
    ctypedef signed long Sint32
    ctypedef unsigned long long Uint64
    ctypedef signed long long Sint64
    ctypedef signed short Sint16
    ctypedef unsigned short Uint16
    ctypedef Uint16 SDL_AudioFormat

    int SDL_AUDIO_ALLOW_FREQUENCY_CHANGE
    int SDL_AUDIO_ALLOW_FORMAT_CHANGE
    int SDL_AUDIO_ALLOW_CHANNELS_CHANGE
    int SDL_AUDIO_ALLOW_ANY_CHANGE

    enum Enum_temp_random_970738:
        SDL_FALSE
        SDL_TRUE
    ctypedef Enum_temp_random_970738 SDL_bool

    int SDL_INIT_AUDIO
    int AUDIO_S16SYS

    int SDL_MIX_MAXVOLUME

    bint SDL_AUDIO_ISLITTLEENDIAN(SDL_AudioFormat format)
    int SDL_AUDIO_BITSIZE(SDL_AudioFormat)

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

    ctypedef Uint32 SDL_AudioDeviceID
    SDL_AudioDeviceID SDL_OpenAudioDevice(char *device, int iscapture, SDL_AudioSpec *desired, SDL_AudioSpec *obtained, int allowed_changes)
    void SDL_LockAudioDevice(SDL_AudioDeviceID dev)
    void SDL_UnlockAudioDevice(SDL_AudioDeviceID dev)
    cdef enum Enum_temp_random_404053:
        SDL_AUDIO_STOPPED
        SDL_AUDIO_PLAYING
        SDL_AUDIO_PAUSED
    ctypedef Enum_temp_random_404053 SDL_AudioStatus
    SDL_AudioStatus SDL_GetAudioStatus()
    SDL_AudioStatus SDL_GetAudioDeviceStatus(SDL_AudioDeviceID dev)
    void SDL_PauseAudioDevice(SDL_AudioDeviceID dev, int pause_on)

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

    void SDL_SetError(char *fmt)
    char *SDL_GetError()
    void SDL_ClearError()

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

    struct SDL_AudioCVT:
        pass
    ctypedef void (*SDL_AudioFilter)(SDL_AudioCVT* cvt, SDL_AudioFormat format)
    struct SDL_AudioCVT:
        int needed
        SDL_AudioFormat src_format
        SDL_AudioFormat dst_format
        double rate_incr
        Uint8 *buf
        int len
        int len_cvt
        int len_mult
        double len_ratio
        SDL_AudioFilter filters[10]
        int filter_index

    int RW_SEEK_SET
    int RW_SEEK_CUR
    int RW_SEEK_END

    struct Struct_temp_random_697984:
        SDL_bool autoclose
        FILE *fp
    struct Struct_temp_random_614396:
        Uint8 *base
        Uint8 *here
        Uint8 *stop
    struct Struct_temp_random_176105:
        void *data1
    union Union_temp_random_505832:
        Struct_temp_random_697984 stdio
        Struct_temp_random_614396 mem
        Struct_temp_random_176105 unknown

    struct SDL_RWops:
        long (*seek)(SDL_RWops* context, long offset, int whence) nogil
        unsigned long (*read)(SDL_RWops* context, void* ptr, size_t size, size_t maxnum) nogil
        unsigned long (*write)(SDL_RWops* context, void* ptr, size_t size, size_t num) nogil
        int (*close)(SDL_RWops* context) nogil
        Uint32 type
        Union_temp_random_505832 hidden

    long SDL_RWseek(SDL_RWops *context, long offset, int whence)
    long SDL_RWtell(SDL_RWops *context)
    unsigned long SDL_RWread(SDL_RWops *context, void* ptr, size_t size, size_t maxnum)
    int SDL_RWclose(SDL_RWops *context)

    SDL_RWops *SDL_RWFromFile(const char *file, const char *mode)

# ---------------------------------------------------------------------------
#    SDL_Mixer
# ---------------------------------------------------------------------------

cdef extern from "SDL_mixer.h" nogil:
    struct Mix_Chunk:
        int allocated
        Uint8 *abuf
        Uint32 alen
        Uint8 volume

    int MIX_MAX_VOLUME

    enum MIX_InitFlags:
        MIX_INIT_FLAC        = 0x00000001,
        MIX_INIT_MP3         = 0x00000008,
        MIX_INIT_OGG         = 0x00000010

    enum Mix_Fading:
        MIX_NO_FADING,
        MIX_FADING_OUT,
        MIX_FADING_IN

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

