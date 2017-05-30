
# ---------------------------------------------------------------------------
#    Definitions from SDL2 library
# ---------------------------------------------------------------------------

cdef extern from "SDL.h":
    ctypedef unsigned char Uint8
    ctypedef unsigned long Uint32
    ctypedef signed long Sint32
    ctypedef unsigned long long Uint64
    ctypedef signed long long Sint64
    ctypedef signed short Sint16
    ctypedef unsigned short Uint16
    ctypedef void *SDL_GLContext
    ctypedef Uint32 SDL_Keycode
    ctypedef Sint32 SDL_JoystickID

    int SDL_WINDOWPOS_UNDEFINED

    ctypedef enum:
        SDL_PIXELFORMAT_ARGB8888
        SDL_PIXELFORMAT_RGBA8888
        SDL_PIXELFORMAT_RGB888
        SDL_PIXELFORMAT_ABGR8888
        SDL_PIXELFORMAT_BGR888

    ctypedef enum SDL_GLattr:
        SDL_GL_RED_SIZE
        SDL_GL_GREEN_SIZE
        SDL_GL_BLUE_SIZE
        SDL_GL_ALPHA_SIZE
        SDL_GL_BUFFER_SIZE
        SDL_GL_DOUBLEBUFFER
        SDL_GL_DEPTH_SIZE
        SDL_GL_STENCIL_SIZE
        SDL_GL_ACCUM_RED_SIZE
        SDL_GL_ACCUM_GREEN_SIZE
        SDL_GL_ACCUM_BLUE_SIZE
        SDL_GL_ACCUM_ALPHA_SIZE
        SDL_GL_STEREO
        SDL_GL_MULTISAMPLEBUFFERS
        SDL_GL_MULTISAMPLESAMPLES
        SDL_GL_ACCELERATED_VISUAL
        SDL_GL_RETAINED_BACKING
        SDL_GL_CONTEXT_MAJOR_VERSION
        SDL_GL_CONTEXT_MINOR_VERSION
        SDL_GL_CONTEXT_EGL
        SDL_GL_CONTEXT_FLAGS
        SDL_GL_CONTEXT_PROFILE_MASK

    ctypedef enum SDL_BlendMode:
        SDL_BLENDMODE_NONE = 0x00000000
        SDL_BLENDMODE_BLEND = 0x00000001
        SDL_BLENDMODE_ADD = 0x00000002
        SDL_BLENDMODE_MOD = 0x00000004


    ctypedef enum SDL_TextureAccess:
        SDL_TEXTUREACCESS_STATIC
        SDL_TEXTUREACCESS_STREAMING
        SDL_TEXTUREACCESS_TARGET

    ctypedef enum SDL_RendererFlags:
        SDL_RENDERER_SOFTWARE = 0x00000001
        SDL_RENDERER_ACCELERATED = 0x00000002
        SDL_RENDERER_PRESENTVSYNC = 0x00000004

    ctypedef enum SDL_bool:
        SDL_FALSE = 0
        SDL_TRUE = 1

    cdef struct SDL_Rect:
        int x, y
        int w, h

    ctypedef struct SDL_Point:
        int x, y

    cdef struct SDL_Color:
        Uint8 r
        Uint8 g
        Uint8 b
        Uint8 unused

    cdef struct SDL_Palette:
        int ncolors
        SDL_Color *colors
        Uint32 version
        int refcount

    cdef struct SDL_PixelFormat:
        Uint32 format
        SDL_Palette *palette
        Uint8 BitsPerPixel
        Uint8 BytesPerPixel
        Uint8 padding[2]
        Uint32 Rmask
        Uint32 Gmask
        Uint32 Bmask
        Uint32 Amask
        Uint8 Rloss
        Uint8 Gloss
        Uint8 Bloss
        Uint8 Aloss
        Uint8 Rshift
        Uint8 Gshift
        Uint8 Bshift
        Uint8 Ashift
        int refcount
        SDL_PixelFormat *next


    cdef struct SDL_BlitMap

    cdef struct SDL_Surface:
        Uint32 flags
        SDL_PixelFormat *format
        int w, h
        int pitch
        void *pixels
        void *userdata
        int locked
        void *lock_data
        SDL_Rect clip_rect
        SDL_BlitMap *map
        int refcount


    ctypedef enum SDL_EventType:
        SDL_FIRSTEVENT     = 0,
        SDL_DROPFILE       = 0x1000,
        SDL_QUIT           = 0x100
        SDL_WINDOWEVENT    = 0x200
        SDL_SYSWMEVENT
        SDL_KEYDOWN        = 0x300
        SDL_KEYUP
        SDL_TEXTEDITING
        SDL_TEXTINPUT
        SDL_MOUSEMOTION     = 0x400
        SDL_MOUSEBUTTONDOWN = 0x401
        SDL_MOUSEBUTTONUP   = 0x402
        SDL_MOUSEWHEEL      = 0x403
        SDL_INPUTMOTION     = 0x500
        SDL_INPUTBUTTONDOWN
        SDL_INPUTBUTTONUP
        SDL_INPUTWHEEL
        SDL_INPUTPROXIMITYIN
        SDL_INPUTPROXIMITYOUT
        SDL_JOYAXISMOTION  = 0x600
        SDL_JOYBALLMOTION
        SDL_JOYHATMOTION
        SDL_JOYBUTTONDOWN
        SDL_JOYBUTTONUP
        SDL_FINGERDOWN      = 0x700
        SDL_FINGERUP
        SDL_FINGERMOTION
        SDL_TOUCHBUTTONDOWN
        SDL_TOUCHBUTTONUP
        SDL_DOLLARGESTURE   = 0x800
        SDL_DOLLARRECORD
        SDL_MULTIGESTURE
        SDL_CLIPBOARDUPDATE = 0x900
        SDL_EVENT_COMPAT1 = 0x7000
        SDL_EVENT_COMPAT2
        SDL_EVENT_COMPAT3
        SDL_USEREVENT    = 0x8000
        SDL_LASTEVENT    = 0xFFFF
        SDL_APP_TERMINATING
        SDL_APP_LOWMEMORY
        SDL_APP_WILLENTERBACKGROUND
        SDL_APP_DIDENTERBACKGROUND
        SDL_APP_WILLENTERFOREGROUND
        SDL_APP_DIDENTERFOREGROUND

    ctypedef enum SDL_WindowEventID:
        SDL_WINDOWEVENT_NONE           #< Never used */
        SDL_WINDOWEVENT_SHOWN          #< Window has been shown */
        SDL_WINDOWEVENT_HIDDEN         #< Window has been hidden */
        SDL_WINDOWEVENT_EXPOSED        #< Window has been exposed and should be
                                        #     redrawn */
        SDL_WINDOWEVENT_MOVED          #< Window has been moved to data1, data2
                                        # */
        SDL_WINDOWEVENT_RESIZED        #< Window has been resized to data1xdata2 */
        SDL_WINDOWEVENT_SIZE_CHANGED   #< The window size has changed, either as a result of an API call or through the system or user changing the window size. */
        SDL_WINDOWEVENT_MINIMIZED      #< Window has been minimized */
        SDL_WINDOWEVENT_MAXIMIZED      #< Window has been maximized */
        SDL_WINDOWEVENT_RESTORED       #< Window has been restored to normal size
                                        # and position */
        SDL_WINDOWEVENT_ENTER          #< Window has gained mouse focus */
        SDL_WINDOWEVENT_LEAVE          #< Window has lost mouse focus */
        SDL_WINDOWEVENT_FOCUS_GAINED   #< Window has gained keyboard focus */
        SDL_WINDOWEVENT_FOCUS_LOST     #< Window has lost keyboard focus */
        SDL_WINDOWEVENT_CLOSE           #< The window manager requests that the
                                        # window be closed */

    ctypedef enum SDL_RendererFlip:
        SDL_FLIP_NONE = 0x00000000
        SDL_FLIP_HORIZONTAL = 0x00000001
        SDL_FLIP_VERTICAL = 0x00000002

    ctypedef enum SDL_WindowFlags:
        SDL_WINDOW_FULLSCREEN = 0x00000001      #,         /**< fullscreen window */
        SDL_WINDOW_OPENGL = 0x00000002          #,             /**< window usable with OpenGL context */
        SDL_WINDOW_SHOWN = 0x00000004           #,              /**< window is visible */
        SDL_WINDOW_HIDDEN = 0x00000008          #,             /**< window is not visible */
        SDL_WINDOW_BORDERLESS = 0x00000010      #,         /**< no window decoration */
        SDL_WINDOW_RESIZABLE = 0x00000020       #,          /**< window can be resized */
        SDL_WINDOW_MINIMIZED = 0x00000040       #,          /**< window is minimized */
        SDL_WINDOW_MAXIMIZED = 0x00000080       #,          /**< window is maximized */
        SDL_WINDOW_INPUT_GRABBED = 0x00000100   #,      /**< window has grabbed input focus */
        SDL_WINDOW_INPUT_FOCUS = 0x00000200     #,        /**< window has input focus */
        SDL_WINDOW_MOUSE_FOCUS = 0x00000400     #,        /**< window has mouse focus */
        SDL_WINDOW_FOREIGN = 0x00000800         #            /**< window not created by SDL */
        SDL_WINDOW_FULLSCREEN_DESKTOP
        SDL_WINDOW_ALLOW_HIGHDPI

    cdef struct SDL_DropEvent:
        Uint32 type
        Uint32 timestamp
        char* file

    cdef struct SDL_MouseMotionEvent:
        Uint32 type
        Uint32 timestamp
        Uint32 windowID
        Uint32 which
        Uint32 state
        Sint32 x
        Sint32 y
        Sint32 xrel
        Sint32 yrel

    cdef struct SDL_MouseButtonEvent:
        Uint32 type
        Uint32 timestamp
        Uint32 windowID
        Uint32 which
        Uint8 button
        Uint8 state
        Uint8 clicks
        Sint32 x
        Sint32 y

    cdef struct SDL_WindowEvent:
        Uint32 type
        Uint32 timestamp
        Uint32 windowID
        Uint8 event
        Sint32 data1
        Sint32 data2

    ctypedef Sint64 SDL_TouchID
    ctypedef Sint64 SDL_FingerID

    cdef struct SDL_TouchFingerEvent:
        Uint32 type
        Uint32 windowID
        SDL_TouchID touchId
        SDL_FingerID fingerId
        float x
        float y
        float dx
        float dy
        float pressure

    cdef struct SDL_Keysym:
        SDL_Scancode scancode       # SDL physical key code - see ::SDL_Scancode for details */
        SDL_Keycode sym             # SDL virtual key code - see ::SDL_Keycode for details */
        Uint16 mod                  # current key modifiers */
        Uint32 unused

    cdef struct SDL_KeyboardEvent:
        Uint32 type         # ::SDL_KEYDOWN or ::SDL_KEYUP
        Uint32 timestamp
        Uint32 windowID     # The window with keyboard focus, if any
        Uint8 state         # ::SDL_PRESSED or ::SDL_RELEASED
        Uint8 repeat        # Non-zero if this is a key repeat
        SDL_Keysym keysym   # The key that was pressed or released

    cdef struct SDL_TextEditingEvent:
        Uint32 type                                 # ::SDL_TEXTEDITING */
        Uint32 timestamp
        Uint32 windowID                             # The window with keyboard focus, if any */
        char *text                                  # The editing text */
        Sint32 start                                # The start cursor of selected editing text */
        Sint32 length                               # The length of selected editing text */

    cdef struct SDL_TextInputEvent:
        Uint32 type                               # ::SDL_TEXTINPUT */
        Uint32 timestamp
        Uint32 windowID                           # The window with keyboard focus, if any */
        char *text                                # The input text */

    cdef struct SDL_MouseWheelEvent:
        Uint32 type
        Uint32 windowID
        int x
        int y
    cdef struct SDL_JoyAxisEvent:
        Uint32 type
        Uint32 timestamp
        SDL_JoystickID which
        Uint8 axis
        Sint16 value
    cdef struct SDL_JoyBallEvent:
        Uint32 type
        Uint32 timestamp
        SDL_JoystickID which
        Uint8 ball
        Sint16  xrel
        Sint16  yrel
    cdef struct SDL_JoyHatEvent:
        Uint32 type
        Uint32 timestamp
        SDL_JoystickID which
        Uint8 hat
        Uint8 value
    cdef struct SDL_JoyButtonEvent:
        Uint32 type
        Uint32 timestamp
        SDL_JoystickID which
        Uint8 button
        Uint8 state
    cdef struct SDL_QuitEvent:
        pass
    cdef struct SDL_UserEvent:
        Uint32 type
        Uint32 timestamp
        Uint32 windowID
        int code
        void *data1
        void *data2

    cdef struct SDL_SysWMEvent:
        pass
    cdef struct SDL_TouchButtonEvent:
        pass
    cdef struct SDL_MultiGestureEvent:
        pass
    cdef struct SDL_DollarGestureEvent:
        pass

    cdef union SDL_Event:
        Uint32 type
        SDL_WindowEvent window
        SDL_KeyboardEvent key
        SDL_TextEditingEvent edit
        SDL_TextInputEvent text
        SDL_MouseMotionEvent motion
        SDL_MouseButtonEvent button
        SDL_DropEvent drop
        SDL_MouseWheelEvent wheel
        SDL_JoyAxisEvent jaxis
        SDL_JoyBallEvent jball
        SDL_JoyHatEvent jhat
        SDL_JoyButtonEvent jbutton
        SDL_QuitEvent quit
        SDL_UserEvent user
        SDL_SysWMEvent syswm
        SDL_TouchFingerEvent tfinger
        SDL_TouchButtonEvent tbutton
        SDL_MultiGestureEvent mgesture
        SDL_DollarGestureEvent dgesture

    cdef struct SDL_RendererInfo:
        char *name
        Uint32 flags
        Uint32 num_texture_formats
        Uint32 texture_formats[16]
        int max_texture_width
        int max_texture_height

    ctypedef struct SDL_Texture
    ctypedef struct SDL_Renderer
    ctypedef struct SDL_Window
    ctypedef struct SDL_DisplayMode:
        Uint32 format
        int w
        int h
        int refresh_rate
        void *driverdata

    cdef struct SDL_RWops:
        long (* seek) (SDL_RWops * context, long offset,int whence)
        size_t(* read) ( SDL_RWops * context, void *ptr, size_t size, size_t maxnum)
        size_t(* write) (SDL_RWops * context, void *ptr,size_t size, size_t num)
        int (* close) (SDL_RWops * context)

    cdef enum SDL_Keymod:
        KMOD_NONE
        KMOD_LSHIFT
        KMOD_RSHIFT
        KMOD_LCTRL
        KMOD_RCTRL
        KMOD_LALT
        KMOD_RALT
        KMOD_LGUI
        KMOD_RGUI
        KMOD_NUM
        KMOD_CAPS
        KMOD_MODE
        KMOD_RESERVED

    ctypedef enum SDL_Scancode:
        pass

    ctypedef int SDL_EventFilter(void* userdata, SDL_Event* event)

    cdef char *SDL_HINT_ORIENTATIONS
    cdef char *SDL_HINT_VIDEO_WIN_D3DCOMPILER
    cdef char *SDL_HINT_ACCELEROMETER_AS_JOYSTICK

    cdef int SDL_QUERY               = -1
    cdef int SDL_IGNORE              =  0
    cdef int SDL_DISABLE             =  0
    cdef int SDL_ENABLE              =  1
    cdef int SDL_INIT_TIMER          = 0x00000001
    cdef int SDL_INIT_AUDIO          = 0x00000010
    cdef int SDL_INIT_VIDEO          = 0x00000020  # SDL_INIT_VIDEO implies SDL_INIT_EVENTS */
    cdef int SDL_INIT_JOYSTICK       = 0x00000200  # SDL_INIT_JOYSTICK implies SDL_INIT_EVENTS */
    cdef int SDL_INIT_HAPTIC         = 0x00001000
    cdef int SDL_INIT_GAMECONTROLLER = 0x00002000  # SDL_INIT_GAMECONTROLLER implies SDL_INIT_JOYSTICK */
    cdef int SDL_INIT_EVENTS         = 0x00004000
    cdef int SDL_INIT_NOPARACHUTE    = 0x00100000  # Don't catch fatal signals */

    cdef SDL_Renderer * SDL_CreateRenderer(SDL_Window * window, int index, Uint32 flags)
    cdef void SDL_DestroyRenderer (SDL_Renderer * renderer)
    cdef SDL_Texture * SDL_CreateTexture(SDL_Renderer * renderer, Uint32 format, int access, int w, int h)
    cdef SDL_Texture * SDL_CreateTextureFromSurface(SDL_Renderer * renderer, SDL_Surface * surface)
    cdef SDL_Surface * SDL_CreateRGBSurface(Uint32 flags, int width, int height, int depth, Uint32 Rmask, Uint32 Gmask, Uint32 Bmask, Uint32 Amask) nogil
    cdef int SDL_RenderCopy(SDL_Renderer * renderer, SDL_Texture * texture, SDL_Rect * srcrect, SDL_Rect * dstrect)
    cdef int SDL_RenderCopyEx(SDL_Renderer * renderer, SDL_Texture * texture, SDL_Rect * srcrect, SDL_Rect * dstrect, double angle, SDL_Point *center, SDL_RendererFlip flip)
    cdef void SDL_RenderPresent(SDL_Renderer * renderer)
    cdef SDL_bool SDL_RenderTargetSupported(SDL_Renderer *renderer)
    cdef int SDL_SetRenderTarget(SDL_Renderer *renderer, SDL_Texture *texture)
    cdef void SDL_DestroyTexture(SDL_Texture * texture)
    cdef void SDL_FreeSurface(SDL_Surface * surface) nogil
    cdef int SDL_SetSurfaceBlendMode(SDL_Surface * surface, int blendMode)
    cdef int SDL_SetSurfaceAlphaMod(SDL_Surface * surface, char alpha)
    cdef int SDL_UpperBlit (SDL_Surface * src, SDL_Rect * srcrect, SDL_Surface * dst, SDL_Rect * dstrect)
    cdef int SDL_BlitSurface(SDL_Surface * src, SDL_Rect * srcrect, SDL_Surface * dst, SDL_Rect * dstrect)
    cdef int SDL_LockTexture(SDL_Texture * texture, SDL_Rect * rect, void **pixels, int *pitch)
    cdef void SDL_UnlockTexture(SDL_Texture * texture)
    cdef void SDL_GetWindowSize(SDL_Window * window, int *w, int *h)
    cdef Uint32 SDL_GetWindowFlags(SDL_Window * window)
    cdef SDL_Window * SDL_CreateWindow(char *title, int x, int y, int w, int h, Uint32 flags)
    cdef void SDL_DestroyWindow (SDL_Window * window)
    cdef int SDL_SetRenderDrawColor(SDL_Renderer * renderer, Uint8 r, Uint8 g, Uint8 b, Uint8 a)
    cdef int SDL_RenderClear(SDL_Renderer * renderer)
    cdef int SDL_SetTextureBlendMode(SDL_Texture * texture, SDL_BlendMode blendMode)
    cdef int SDL_GetTextureBlendMode(SDL_Texture * texture, SDL_BlendMode *blendMode)
    cdef SDL_Surface * SDL_CreateRGBSurfaceFrom(void *pixels, int width, int height, int depth, int pitch, Uint32 Rmask, Uint32 Gmask, Uint32 Bmask, Uint32 Amask)
    cdef SDL_Surface* SDL_ConvertSurface(SDL_Surface* src, SDL_PixelFormat* fmt, Uint32 flags)
    cdef SDL_Surface* SDL_ConvertSurfaceFormat(SDL_Surface* src, Uint32
            pixel_format, Uint32 flags)
    cdef const char* SDL_GetPixelFormatName(Uint32 format)
    cdef int SDL_Init(Uint32 flags)
    cdef void SDL_Quit()
    cdef int SDL_EnableUNICODE(int enable)
    cdef Uint32 SDL_GetTicks()
    cdef void SDL_Delay(Uint32 ms) nogil
    cdef Uint8 SDL_EventState(Uint32 type, int state)
    cdef int SDL_PollEvent(SDL_Event * event) nogil
    cdef void SDL_SetEventFilter(SDL_EventFilter *filter, void* userdata)
    cdef SDL_RWops * SDL_RWFromFile(char *file, char *mode)
    cdef SDL_RWops * SDL_RWFromMem(void *mem, int size)
    cdef SDL_RWops * SDL_RWFromConstMem(void *mem, int size)
    cdef void SDL_FreeRW(SDL_RWops *area)
    cdef int SDL_GetRendererInfo(SDL_Renderer *renderer, SDL_RendererInfo *info)
    cdef int SDL_RenderSetViewport(SDL_Renderer * renderer, SDL_Rect * rect)
    cdef int SDL_GetCurrentDisplayMode(int displayIndex, SDL_DisplayMode * mode)
    cdef int SDL_GetDesktopDisplayMode(int displayIndex, SDL_DisplayMode * mode)
    cdef int SDL_SetTextureColorMod(SDL_Texture * texture, Uint8 r, Uint8 g, Uint8 b)
    cdef int SDL_SetTextureAlphaMod(SDL_Texture * texture, Uint8 alpha)
    cdef char * SDL_GetError()
    cdef SDL_bool SDL_SetHint(char *name, char *value)
    cdef Uint8 SDL_GetMouseState(int* x,int* y)
    cdef SDL_GLContext SDL_GL_CreateContext(SDL_Window* window)
    cdef int SDL_GetNumVideoDisplays()
    cdef int SDL_GetNumDisplayModes(int displayIndex)
    cdef int SDL_GetDisplayMode(int displayIndex, int index, SDL_DisplayMode * mode)
    cdef SDL_bool SDL_HasIntersection(SDL_Rect * A, SDL_Rect * B) nogil
    cdef SDL_bool SDL_IntersectRect(SDL_Rect * A, SDL_Rect * B, SDL_Rect * result) nogil
    cdef void SDL_UnionRect(SDL_Rect * A, SDL_Rect * B, SDL_Rect * result) nogil
    cdef Uint64 SDL_GetPerformanceCounter() nogil
    cdef Uint64 SDL_GetPerformanceFrequency() nogil
    cdef int SDL_GL_SetAttribute(SDL_GLattr attr, int value)
    cdef int SDL_GetNumRenderDrivers()
    cdef int SDL_GetRenderDriverInfo(int index, SDL_RendererInfo* info)
    cdef int SDL_GL_BindTexture(SDL_Texture *texture, float *texw, float *texh)
    cdef int SDL_GL_UnbindTexture(SDL_Texture *texture)
    cdef int SDL_RenderReadPixels(SDL_Renderer * renderer, SDL_Rect * rect, Uint32 format, void *pixels, int pitch) nogil
    cdef int SDL_PushEvent(SDL_Event * event) nogil
    cdef int SDL_WaitEvent(SDL_Event * event) nogil

    cdef void SDL_SetClipboardText(char * text)
    cdef const char * SDL_GetClipboardText()
    cdef SDL_bool SDL_HasClipboardText()
    cdef int SDL_GetNumVideoDrivers()
    cdef const char *SDL_GetVideoDriver(int index)
    cdef int SDL_VideoInit(const char *driver_name)
    cdef void SDL_VideoQuit()
    cdef const char *SDL_GetCurrentVideoDriver()
    cdef int SDL_GetNumVideoDisplays()
    cdef const char * SDL_GetDisplayName(int displayIndex)
    cdef int SDL_GetDisplayBounds(int displayIndex, SDL_Rect * rect)
    cdef int SDL_GetNumDisplayModes(int displayIndex)
    cdef int SDL_GetDesktopDisplayMode(int displayIndex, SDL_DisplayMode * mode)
    cdef int SDL_GetCurrentDisplayMode(int displayIndex, SDL_DisplayMode * mode)
    cdef SDL_DisplayMode * SDL_GetClosestDisplayMode(int displayIndex, const SDL_DisplayMode * mode, SDL_DisplayMode * closest)
    cdef int SDL_SetWindowDisplayMode(SDL_Window * window, SDL_DisplayMode * mode)
    cdef int SDL_GetWindowDisplayMode(SDL_Window * window, SDL_DisplayMode * mode)
    cdef int SDL_GetWindowDisplayIndex(SDL_Window * window)
    cdef Uint32 SDL_GetWindowPixelFormat(SDL_Window * window)
    cdef SDL_Window * SDL_CreateWindowFrom(const void *data)
    cdef Uint32 SDL_GetWindowID(SDL_Window * window)
    cdef SDL_Window * SDL_GetWindowFromID(Uint32 id)
    cdef Uint32 SDL_GetWindowFlags(SDL_Window * window)
    cdef void SDL_SetWindowTitle(SDL_Window * window, char *title)
    cdef const char *SDL_GetWindowTitle(SDL_Window * window)
    cdef void SDL_SetWindowIcon(SDL_Window * window, SDL_Surface *icon)
    cdef void* SDL_SetWindowData(SDL_Window * window, char *name, void *data)
    cdef void *SDL_GetWindowData(SDL_Window * window, char *name)
    cdef void SDL_SetWindowPosition(SDL_Window * window, int x, int y)
    cdef void SDL_GetWindowPosition(SDL_Window * window, int *x, int *y)
    cdef void SDL_SetWindowSize(SDL_Window * window, int w, int h)
    cdef void SDL_GetWindowSize(SDL_Window * window, int *w, int *h)
    cdef void SDL_SetWindowMinimumSize(SDL_Window * window, int min_w, int min_h)
    cdef void SDL_SetWindowBordered(SDL_Window * window, SDL_bool bordered)
    cdef void SDL_ShowWindow(SDL_Window * window)
    cdef int SDL_ShowCursor(int toggle)
    cdef void SDL_HideWindow(SDL_Window * window)
    cdef void SDL_RaiseWindow(SDL_Window * window)
    cdef void SDL_MaximizeWindow(SDL_Window * window)
    cdef void SDL_MinimizeWindow(SDL_Window * window)
    cdef void SDL_RestoreWindow(SDL_Window * window)
    cdef int SDL_SetWindowFullscreen(SDL_Window * window, SDL_bool fullscreen)
    cdef SDL_Surface * SDL_GetWindowSurface(SDL_Window * window)
    cdef int SDL_UpdateWindowSurface(SDL_Window * window)
    cdef void SDL_SetWindowGrab(SDL_Window * window, SDL_bool grabbed)
    cdef SDL_bool SDL_GetWindowGrab(SDL_Window * window)
    cdef int SDL_SetWindowBrightness(SDL_Window * window, float brightness)
    cdef float SDL_GetWindowBrightness(SDL_Window * window)
    cdef void SDL_DestroyWindow(SDL_Window * window)
    cdef SDL_bool SDL_IsScreenSaverEnabled()
    cdef void SDL_EnableScreenSaver()
    cdef void SDL_DisableScreenSaver()
    cdef int SDL_GL_LoadLibrary(const char *path)
    cdef void *SDL_GL_GetProcAddress(const char *proc)
    cdef void SDL_GL_UnloadLibrary()
    cdef int SDL_GL_SetAttribute(SDL_GLattr attr, int value)
    cdef int SDL_GL_GetAttribute(SDL_GLattr attr, int *value)
    cdef int SDL_GL_MakeCurrent(SDL_Window * window, SDL_GLContext context)
    cdef SDL_Window* SDL_GL_GetCurrentWindow()
    cdef SDL_GLContext SDL_GL_GetCurrentContext()
    cdef int SDL_GL_SetSwapInterval(int interval)
    cdef int SDL_GL_GetSwapInterval()
    cdef void SDL_GL_SwapWindow(SDL_Window * window)
    cdef void SDL_GL_DeleteContext(SDL_GLContext context)

    cdef SDL_Window * SDL_GetKeyboardFocus()
    cdef Uint8 *SDL_GetKeyboardState(int *numkeys)
    cdef SDL_Keymod SDL_GetModState()
    cdef void SDL_SetModState(SDL_Keymod modstate)
    cdef SDL_Keycode SDL_GetKeyFromScancode(SDL_Scancode scancode)
    cdef SDL_Scancode SDL_GetScancodeFromKey(SDL_Keycode key)
    cdef char *SDL_GetScancodeName(SDL_Scancode scancode)
    cdef SDL_Scancode SDL_GetScancodeFromName(char *name)
    cdef char *SDL_GetKeyName(SDL_Keycode key)
    cdef SDL_Keycode SDL_GetKeyFromName(char *name)
    cdef void SDL_StartTextInput()
    cdef SDL_bool SDL_IsTextInputActive()
    cdef void SDL_StopTextInput()
    cdef void SDL_SetTextInputRect(SDL_Rect *rect)
    cdef SDL_bool SDL_HasScreenKeyboardSupport()
    cdef SDL_bool SDL_IsScreenKeyboardShown(SDL_Window *window)
    cdef void SDL_GL_GetDrawableSize(SDL_Window *window, int *w, int *h)

cdef extern from "SDL_image.h":
    ctypedef enum IMG_InitFlags:
        IMG_INIT_JPG
        IMG_INIT_PNG
        IMG_INIT_TIF
        IMG_INIT_WEBP
    cdef int IMG_Init(IMG_InitFlags flags)
    cdef char *IMG_GetError()
    cdef SDL_Surface *IMG_Load(char *file)
    cdef SDL_Surface *IMG_Load_RW(SDL_RWops *src, int freesrc)
    cdef SDL_Surface *IMG_LoadTyped_RW(SDL_RWops *src, int freesrc, char *type)
    cdef int *IMG_SavePNG(SDL_Surface *src, char *file)

