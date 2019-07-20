cdef extern from *:
    ctypedef bint bool

# ---------------------------------------------------------------------------
#    GStreamer declarations from gst.h
# ---------------------------------------------------------------------------
cdef extern from 'gst/gst.h':
    ctypedef void *GstPipeline
    ctypedef void *GstElement
    ctypedef void *GstBus
    ctypedef void *GstPad
    ctypedef void *GstSample
    ctypedef void *GstBuffer
    ctypedef void *GstMemory
    ctypedef void *GstBin
    ctypedef void *GstCaps
    ctypedef void *GstTimedValueControlSource
    ctypedef void *GstQuery
    ctypedef void *GObject
    ctypedef void (*appcallback_t)(void *, int, int, char *, int)
    ctypedef void (*buscallback_t)(void *, GstMessage *)
    ctypedef unsigned int guint
    ctypedef unsigned long gulong
    ctypedef unsigned char guint8
    ctypedef unsigned int guint32
    ctypedef unsigned int gsize
    ctypedef void *gpointer
    ctypedef const void *gconstpointer
    ctypedef char gchar
    ctypedef char const_gchar 'const gchar'
    ctypedef int gint
    ctypedef long int gint64
    ctypedef unsigned long long GstClockTime
    ctypedef int gboolean

    ctypedef enum GstState:
        GST_STATE_VOID_PENDING
        GST_STATE_NULL
        GST_STATE_READY
        GST_STATE_PAUSED
        GST_STATE_PLAYING

    ctypedef enum GstFormat:
        GST_FORMAT_DEFAULT
        GST_FORMAT_BYTES
        GST_FORMAT_TIME

    ctypedef enum GstSeekFlags:
        GST_SEEK_FLAG_KEY_UNIT
        GST_SEEK_FLAG_FLUSH

    ctypedef enum GstStateChangeReturn:
        pass

    ctypedef struct GError:
        int code
        char *message

    ctypedef struct GstAudioInfo:
        gint rate
        gint channels
        gint bpf

    ctypedef struct GstMapInfo:
        GstMemory *memory
        GstMapFlags flags
        guint8 *data
        gsize size
        gsize maxsize

    ctypedef enum GstMapFlags:
        GST_MAP_READ
        GST_MAP_WRITE
        GST_MAP_FLAG_LAST

    ctypedef enum GstMessageType:
        GST_MESSAGE_EOS
        GST_MESSAGE_ERROR
        GST_MESSAGE_WARNING
        GST_MESSAGE_INFO

    ctypedef struct GstMessage:
        GstMessageType type

    int GST_SECOND
    bool gst_init_check(int *argc, char ***argv, GError **error)
    bool gst_is_initialized()
    void gst_deinit()
    void gst_version(guint *major, guint *minor, guint *micro, guint *nano)
    GstElement *gst_parse_launch(const_gchar *pipeline_description, GError **error)
    GstElement *gst_element_factory_make(const_gchar *factoryname, const_gchar *name)
    GstElement *gst_bin_new(const_gchar *name)
    bool gst_bin_add(GstBin *bin, GstElement *element)
    bool gst_bin_remove(GstBin *bin, GstElement *element)
    GstElement *gst_bin_get_by_name(GstBin *bin, const_gchar *name)
    void gst_object_unref(void *pointer) nogil
    bool gst_element_query(GstElement *element, GstQuery *query)
    GstQuery *gst_query_new_duration(GstFormat format)
    void gst_query_parse_duration(GstQuery *query, GstFormat *format, gint64 *duration)
    void gst_query_unref(GstQuery *q)
    GstElement *gst_pipeline_new(const_gchar *name)
    GstPad *gst_element_get_static_pad(GstElement *element, const_gchar *name)
    GstPad *gst_element_get_request_pad(GstElement *element, const_gchar *name)
    void gst_element_release_request_pad(GstElement *element, GstPad *pad)
    GstPad *gst_ghost_pad_new(const_gchar *name, GstPad *target)
    bool gst_element_add_pad(GstElement *element, GstPad *pad)
    void gst_bus_enable_sync_message_emission(GstBus *bus)
    GstBus *gst_pipeline_get_bus(GstPipeline *pipeline)
    GstBuffer *gst_sample_get_buffer(GstSample *sample) nogil
    void gst_buffer_unref(GstBuffer *buffer) nogil
    void gst_sample_unref(GstSample *sample) nogil
    gboolean gst_buffer_map(GstBuffer *buffer, GstMapInfo *info, GstMapFlags flags) nogil
    void gst_buffer_unmap(GstBuffer *buffer, GstMapInfo *info) nogil
    GstCaps *gst_sample_get_caps(GstSample *sample)
    GstStateChangeReturn gst_element_get_state(
            GstElement *element, GstState *state, GstState *pending,
            GstClockTime timeout) nogil
    GstStateChangeReturn gst_element_set_state(
            GstElement *element, GstState state) nogil
    void g_signal_emit_by_name(gpointer instance, const_gchar *detailed_signal,
            void *retvalue)
    GstCaps *gst_caps_from_string(const_gchar *string)
    void gst_caps_unref(GstCaps *caps)
    bool gst_audio_info_from_caps(GstAudioInfo *info, const GstCaps *caps)
    void g_error_free(GError *error)
    bool gst_element_link(GstElement *src, GstElement *dest) nogil
    bool gst_element_link_filtered(GstElement *src, GstElement *dest, GstCaps *filter) nogil
    bool gst_element_query_position(
            GstElement *element, GstFormat format, gint64 *cur) nogil
    bool gst_element_query_duration(
            GstElement *element, GstFormat format, gint64 *cur) nogil
    bool gst_element_seek_simple(
            GstElement *element, GstFormat format,
            GstSeekFlags seek_flags, gint64 seek_pos) nogil
    void gst_message_parse_error(
            GstMessage *message, GError **gerror, char **debug)
    void gst_message_parse_warning(
            GstMessage *message, GError **gerror, char **debug)
    void gst_message_parse_info(
            GstMessage *message, GError **gerror, char **debug)


# ---------------------------------------------------------------------------
#    glib declarations from glib.h
# ---------------------------------------------------------------------------
cdef extern from 'glib.h':
    int glib_major_version
    int glib_minor_version
    int glib_micro_version

    ctypedef void (*GFunc)(gpointer data, gpointer user_data)

    # Memory management
    ctypedef void (*GDestroyNotify)(gpointer data)
    ctypedef gpointer (*GReallocFunc)(gpointer data, gsize size)
    void g_free(gpointer mem)
    gpointer g_malloc(gsize n_bytes)
    gpointer g_realloc(gpointer mem, gsize n_bytes)

    # Linked list
    ctypedef _GSList GSList
    ctypedef struct _GSList:
        gpointer data
        GSList *next
    GSList* g_slist_append(GSList *list, gpointer data) nogil
    GSList* g_slist_prepend(GSList *list, gpointer data) nogil
    GSList* g_slist_remove(GSList *list, gconstpointer data) nogil
    void g_slist_free (GSList *list) nogil
    guint g_slist_length (GSList *list) nogil
    GSList *g_slist_reverse(GSList *list) nogil
    void g_slist_foreach(GSList *list, GFunc func, gpointer user_data) nogil
    gpointer g_slist_nth_data(GSList *list, guint n) nogil

    # Memory slices
    gpointer g_slice_alloc(gsize block_size) nogil
    gpointer g_slice_alloc0(gsize block_size) nogil
    void g_slice_free1(gsize block_size, gpointer mem_block) nogil
    gpointer g_slice_copy(gsize block_size, gconstpointer mem_block) nogil

    # Array
    ctypedef struct GArray:
        gchar *data
        guint len
    GArray *g_array_new(gboolean zero_terminated, gboolean clear_, guint element_size) nogil
    GArray *g_array_sized_new(gboolean zero_terminated, gboolean clear_, guint element_size, guint reserved_size) nogil
    GArray *g_array_set_size(GArray *array, guint length) nogil
    gchar *g_array_free(GArray *array, gboolean free_segment) nogil

# ---------------------------------------------------------------------------
#    GStreamer helper functions defined in gstreamer_helper.h
# ---------------------------------------------------------------------------
cdef extern from 'gstreamer_helper.h':
    void g_gst_log_error(const_gchar *file, const_gchar *function, gint line, GObject *object, const_gchar *message) nogil
    void g_gst_log_warning(const_gchar *file, const_gchar *function, gint line, GObject *object, const_gchar *message) nogil
    void g_gst_log_info(const_gchar *file, const_gchar *function, gint line, GObject *object, const_gchar *message) nogil
    void g_gst_log_debug(const_gchar *file, const_gchar *function, gint line, GObject *object, const_gchar *message) nogil
    gboolean g_object_get_bool(GstElement *element, char *name) nogil
    GstSample *c_appsink_pull_preroll(GstElement *appsink) nogil
    GstSample *c_appsink_pull_sample(GstElement *appsink) nogil
    gulong c_bus_connect_message(GstBus *bus,
            buscallback_t callback, void *userdata)
    void c_signal_disconnect(GstElement *appsink, gulong handler_id)

    void g_array_insert_val_uint(GArray *array, guint index, guint value) nogil
    void g_array_insert_val_uint8(GArray *array, guint index, guint8 value) nogil
    guint g_array_index_uint(GArray* array, guint index) nogil
    guint8 g_array_index_uint8(GArray* array, guint index) nogil
    void g_array_set_val_uint(GArray *array, guint index, guint value) nogil
    void g_array_set_val_uint8(GArray *array, guint index, guint8 value) nogil
