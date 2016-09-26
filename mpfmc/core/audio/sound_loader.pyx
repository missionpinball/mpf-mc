#!python
#cython: embedsignature=True, language_level=3
"""
Sound loader

This library requires both the GStreamer library.
"""

from cpython.mem cimport PyMem_Malloc, PyMem_Free
import cython

include "gstreamer.pxi"


# ---------------------------------------------------------------------------
#    SoundLoader class
# ---------------------------------------------------------------------------
cdef class SoundLoader:
    """
    The SoundLoader class supports loading sound files using the GStreamer library
    """

    cdef GstElement *pipeline
    cdef GstElement *sink
    cdef GError *error
    cdef GstStateChangeReturn ret
    cdef GstState state
    cdef GstCaps *caps
    cdef GstSample *sample
    cdef GstBuffer *buffer
    cdef GstAudioInfo audio_info
    cdef gint64 duration = -1

    def __cinit__(self, *args, **kw):
        pass

    def __init__(self, rate=44100, channels=2, buffer_samples=4096):
        pass



