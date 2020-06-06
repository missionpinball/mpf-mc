from mpfmc.core.audio.sdl2 cimport *
from mpfmc.core.audio.gstreamer cimport *


ctypedef struct SampleMemory:
    gpointer data
    gsize size

ctypedef struct SampleStream:
    GstElement *pipeline
    GstElement *sink
    GstSample *sample
    GstBuffer *buffer
    GstMapInfo map_info
    Uint32 map_buffer_pos
    gboolean map_contains_valid_sample_data
    gint null_buffer_count

cdef enum SoundType:
    sound_type_memory = 0
    sound_type_streaming = 1

ctypedef union SoundSampleData:
    SampleMemory *memory
    SampleStream *stream

ctypedef struct SoundSample:
    SoundType type
    SoundSampleData data
    double duration
    Uint32 size


cdef class SoundFile:
    """SoundFile is the base class for wrapper classes used to manage sound sample data."""
    cdef str file_name
    cdef AudioCallbackData *callback_data
    cdef SoundSample sample
    cdef object log


cdef class SoundMemoryFile(SoundFile):
    """SoundMemoryFile is a wrapper class to manage sound sample data stored
    in memory."""
    cdef bint _loaded_using_sdl


cdef class SoundStreamingFile(SoundFile):
    """SoundStreamingFile is a wrapper class to manage streaming sound sample data."""
    cdef GstElement *pipeline
    cdef GstElement *source
    cdef GstElement *convert
    cdef GstElement *resample
    cdef GstElement *sink
    cdef GstBus *bus
    cdef gulong bus_message_handler_id
