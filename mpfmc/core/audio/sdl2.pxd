# ---------------------------------------------------------------------------
#    Definitions from SDL2 library
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
        SDL_AudioFormat format
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
    void SDL_CloseAudioDevice(SDL_AudioDeviceID dev)

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
    int SDL_InitSubSystem(Uint32 flags)
    void SDL_Quit()
    void SDL_LockAudio()
    void SDL_UnlockAudio()
    void SDL_MixAudio(Uint8 *dst, const Uint8 *src, Uint32 len, int volume)
    void SDL_MixAudioFormat(Uint8 *dst, const Uint8 *src, SDL_AudioFormat format,
                                                Uint32 len, int volume)
    SDL_AudioSpec* SDL_LoadWAV(const char* file, SDL_AudioSpec* spec, Uint8** audio_buf, Uint32* audio_len)
    void SDL_FreeWAV(Uint8* audio_buf)
    void SDL_free(void *ptr)

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

    int SDL_BuildAudioCVT(SDL_AudioCVT *cvt, SDL_AudioFormat src_fmt, Uint8 src_channels, int src_rate,
                          SDL_AudioFormat dst_fmt, Uint8 dst_channels, int dst_rate)
    int SDL_ConvertAudio(SDL_AudioCVT *cvt)

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
#    SDL2 helper functions defined in sdl2_helper.h
# ---------------------------------------------------------------------------
cdef extern from 'sdl2_helper.h':
    int convert_audio_to_desired_format(SDL_AudioSpec input_spec, SDL_AudioSpec desired_spec,
                                        Uint8* input_buffer, Uint32 input_size, Uint8** output_buffer, Uint32 *output_size)


# ---------------------------------------------------------------------------
#    SDL_Mixer
# ---------------------------------------------------------------------------
cdef extern from "SDL_mixer.h" nogil:

    cdef enum MIX_InitFlags:
        MIX_INIT_FLAC,
        MIX_INIT_MP3,
        MIX_INIT_OGG

    struct Mix_Chunk:
        int allocated
        Uint8 *abuf
        Uint32 alen
        Uint8 volume

    int MIX_MAX_VOLUME

    void Mix_Quit()
    int Mix_OpenAudio(int frequency, Uint16 format, int channels, int chunksize)
    void Mix_CloseAudio()
    int Mix_QuerySpec(int *frequency, Uint16 *format, int *channels)
    const SDL_version *Mix_Linked_Version()
    int Mix_AllocateChannels(int numchans)
    void Mix_HookMusic(void (*mix_func)(void *udata, Uint8 *stream, int len), void *arg)
    void *Mix_GetMusicHookData()
    Mix_Chunk *Mix_LoadWAV(char *file)


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

cdef union Sample16:
    # Union structure that represents a single 16-bit sample value.  A union is
    # utilized to make it easy to access the individual bytes in the sample.
    # This is needed since all samples are streamed as individual 8-bit (byte)
    # values.
    Sint16 value
    Sample16Bytes bytes


# ---------------------------------------------------------------------------
#    Audio Callback Data type
# ---------------------------------------------------------------------------

ctypedef struct AudioCallbackData:
    # A pointer to this struct is passed to the main audio callback function and
    # is the only way data is made available to the main audio thread.  Must not
    # contain any Python objects.
    SDL_AudioFormat format
    int sample_rate
    int channels
    Uint16 buffer_samples
    Uint32 buffer_size
    Uint16 bytes_per_control_point
    Uint8 bytes_per_sample
    double seconds_to_bytes_factor
    Uint8 quick_fade_steps
    Uint8 master_volume
    Uint8 silence
    Uint8 track_count
    void **tracks
    FILE *c_log_file
