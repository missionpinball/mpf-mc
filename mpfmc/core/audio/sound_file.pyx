#!python
#cython: embedsignature=True, language_level=3

from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
cimport cpython.pycapsule as pycapsule
import logging
import os

from mpfmc.core.audio.audio_exception import AudioException
from mpfmc.core.audio.sdl2 cimport *
from mpfmc.core.audio.gstreamer cimport *
from mpfmc.core.audio.sound_file cimport *


# ---------------------------------------------------------------------------
#    SoundFile class
# ---------------------------------------------------------------------------
cdef class SoundFile:
    """SoundFile is the base class for wrapper classes used to manage sound sample data."""

    def __init__(self, str file_name, object audio_callback_data):
        self.log = logging.getLogger("SoundFile")
        self.file_name = file_name
        self.callback_data = <AudioCallbackData*>pycapsule.PyCapsule_GetPointer(audio_callback_data, NULL)
        self.sample.duration = 0

    def __repr__(self):
        return '<SoundFile>'

    def load(self):
        """Load the sound file"""
        raise NotImplementedError("Must be implemented in derived class")

    def unload(self):
        """Unload the sound file"""
        raise NotImplementedError("Must be implemented in derived class")

    @property
    def duration(self):
        """Return the duration of the sound file"""
        return self.sample.duration


# ---------------------------------------------------------------------------
#    SoundMemoryFile class
# ---------------------------------------------------------------------------
cdef class SoundMemoryFile(SoundFile):
    """SoundMemoryFile is a wrapper class to manage sound sample data stored
    in memory."""

    def __init__(self, str file_name, object audio_callback_data):
        # IMPORTANT: Call super class init function
        super().__init__(file_name, audio_callback_data)
        self.log = logging.getLogger("SoundMemoryFile")
        self.sample.type = sound_type_memory
        self.sample.data.memory = <SampleMemory*>PyMem_Malloc(sizeof(SampleMemory))
        self.sample.data.memory.data = NULL
        self.sample.data.memory.size = 0

        self.load()

    def __dealloc__(self):
        self.unload()
        if self.sample.data.memory != NULL:
            PyMem_Free(self.sample.data.memory)
            self.sample.data.memory = NULL

    def __repr__(self):
        if self.loaded:
            return '<SoundMemoryFile({}, Loaded=True, sample_duration={}s)>'.format(self.file_name, self.sample.duration)
        else:
            return "<SoundMemoryFile({}, Loaded=False)>".format(self.file_name)

    def load(self):
        """Loads the sound into memory using the most appropriate library for the format."""
        cdef Mix_Chunk *chunk

        if self.loaded:
            return

        if not os.path.isfile(self.file_name):
            raise AudioException('Could not locate file ' + self.file_name)

        # Load the audio file (will be converted to current sample output format)
        chunk = Mix_LoadWAV(self.file_name.encode('utf-8'))
        if chunk == NULL:
            msg = "Could not load sound file {} due to an error: {}".format(self.file_name, SDL_GetError())
            raise AudioException(msg)

        # Save the loaded sample data
        self.sample.data.memory.size = <gsize>chunk.alen
        self.sample.data.memory.data = <gpointer>chunk.abuf

        # Set the sample size (bytes) and  duration (seconds)
        self.sample.size = self.sample.data.memory.size
        self.sample.duration = self.sample.data.memory.size / self.callback_data.seconds_to_bytes_factor

        # Free the chunk (sample memory will not be freed).  The chunk was allocated using SDL_malloc in the
        # SDL_Mixer library.  We do not want to use Mix_Free or the sample data will be freed.  Instead, we
        # can just free the Mix_Chunk structure using SDL_free and the sample buffer will remain intact. The
        # sample memory must be freed later when this object is deallocated.
        SDL_free(chunk)

        self.log.debug('Loaded file: %s Sample duration: %s',
                       self.file_name, self.sample.duration)

    def unload(self):
        """Unloads the sample data from memory"""
        if self.sample.data.memory.data != NULL:
            SDL_free(<void*>self.sample.data.memory.data)

        self.sample.data.memory.data = NULL
        self.sample.data.memory.size = 0

    @property
    def loaded(self):
        """Returns whether or not the sound file data is loaded in memory"""
        return self.sample.data.memory.data != NULL and self.sample.data.memory.size > 0


# ---------------------------------------------------------------------------
#    SoundStreamingFile class
# ---------------------------------------------------------------------------
cdef class SoundStreamingFile(SoundFile):
    """SoundStreamingFile is a wrapper class to manage streaming sound sample data."""

    def __cinit__(self, *args, **kwargs):
        """C constructor"""
        self.pipeline = NULL
        self.bus = NULL
        self.bus_message_handler_id = 0

    def __init__(self, str file_name, object audio_callback_data):
        # IMPORTANT: Call super class init function
        super().__init__(file_name, audio_callback_data)
        self.log = logging.getLogger("SoundStreamingFile")

        self.sample.type = sound_type_streaming
        self.sample.data.stream = <SampleStream*>PyMem_Malloc(sizeof(SampleStream))
        self.sample.data.stream.pipeline = NULL
        self.sample.data.stream.sink = NULL
        self.sample.data.stream.sample = NULL
        self.sample.data.stream.buffer = NULL
        self.sample.data.stream.map_contains_valid_sample_data = 0
        self.sample.data.stream.map_buffer_pos = 0
        self.sample.data.stream.null_buffer_count = 0

        self.load()

    def __dealloc__(self):
        if self.sample.data.stream != NULL:
            PyMem_Free(self.sample.data.stream)
            self.sample.data.stream = NULL

    def __repr__(self):
        if self.loaded:
            return '<SoundStreamingFile({}, Loaded=True, sample_duration={}s)>'.format(self.file_name,self.sample.duration)
        return "<SoundStreamingFile({}, Loaded=False)>".format(self.file_name)

    def _gst_init(self):
        if gst_is_initialized():
            return True
        cdef int argc = 0
        cdef char **argv = NULL
        cdef GError *error
        if not gst_init_check(&argc, &argv, &error):
            msg = 'Unable to initialize gstreamer: code={} message={}'.format(
                    error.code, <bytes>error.message)
            raise AudioException(msg)

    def _destroy_pipeline(self):
        """Destroys the GStreamer pipeline"""
        """Destroys the current pipeline"""
        cdef GstState current_state, pending_state

        if self.bus != NULL and self.bus_message_handler_id != 0:
            c_signal_disconnect(<GstElement*>self.bus, self.bus_message_handler_id)
            self.bus_message_handler_id = 0

        if self.pipeline != NULL:
            # the state changes are async. if we want to guarantee that the
            # state is set to NULL, we need to query it. We also put a 5s
            # timeout for safety, but normally, nobody should hit it.
            with nogil:
                gst_element_set_state(self.pipeline, GST_STATE_NULL)
                gst_element_get_state(self.pipeline, &current_state,
                        &pending_state, <GstClockTime>5e9)
            gst_object_unref(self.pipeline)

        if self.bus != NULL:
            gst_object_unref(self.bus)

        self.bus = NULL
        self.pipeline = NULL

    def _construct_pipeline(self):
        """Creates the GStreamer pipeline used to stream the sound data"""
        cdef GError *error
        cdef GstSample *sample
        cdef gint64 size = 0

        # Pipeline structure: uridecodebin --> audioconvert --> audioresample --> appsink

        # If the pipeline has already been created, delete it
        if self.pipeline != NULL:
            self._destroy_pipeline()

        # Pipeline structure: uridecodebin --> audioconvert --> audioresample --> appsink

        # Create GStreamer pipeline with the specified caps (from a string)
        file_path = 'file:///' + self.file_name.replace('\\', '/')
        if SDL_AUDIO_ISLITTLEENDIAN(self.callback_data.format):
            audio_format = "S16LE"
        else:
            audio_format = "S16BE"
        pipeline_string = 'uridecodebin uri="{}" ! audioconvert ! audioresample ! appsink name=sink caps="audio/x-raw,rate={},channels={},format={},layout=interleaved" sync=true blocksize={}'.format(
            file_path, str(self.callback_data.sample_rate), str(self.callback_data.channels), audio_format, self.callback_data.buffer_size)

        error = NULL
        self.pipeline = gst_parse_launch(pipeline_string.encode('utf-8'), &error)

        if error != NULL:
            msg = 'Unable to create a GStreamer pipeline: code={} message={}'.format(error.code, <bytes>error.message)
            raise AudioException(msg)

        # Get the pipeline bus (the bus allows applications to receive pipeline messages)
        self.bus = gst_pipeline_get_bus(<GstPipeline*>self.pipeline)
        if self.bus == NULL:
            raise AudioException('Unable to get bus from the pipeline')

        # Enable pipeline messages and callback message handler
        #gst_bus_enable_sync_message_emission(self.bus)
        #self.bus_message_handler_id = c_bus_connect_message(self.bus, _on_gst_bus_message, <void*>self.audio_interface)

        # Get sink
        self.sink = gst_bin_get_by_name(<GstBin*>self.pipeline, "sink")

        # Set to PAUSED to make the first frame arrive in the sink
        ret = gst_element_set_state(self.pipeline, GST_STATE_PAUSED)

        # Get the preroll sample (forces the code to wait until the sample has been completely loaded
        # which is necessary to retrieve the duration).
        sample = c_appsink_pull_preroll(self.sink)
        if sample != NULL:
            gst_sample_unref(sample)

        # Get size of audio file (in bytes)
        if not gst_element_query_duration(self.sink, GST_FORMAT_BYTES , &size):
            size = 0

        # Store length and duration (seconds)
        self.sample.size = size
        self.sample.duration = <double>size / self.callback_data.seconds_to_bytes_factor

        # The pipeline should now be ready to play.  Store the pointers to the pipeline
        # and appsink in the SampleStream struct for use in the application.
        self.sample.data.stream.pipeline = self.pipeline
        self.sample.data.stream.sink = self.sink

    def load(self):
        """Loads the sound into memory using GStreamer"""

        #if self.loaded:
        #    return

        self._gst_init()
        self._construct_pipeline()

        self.log.debug('Loaded file: %s Sample duration: %s',
                       self.file_name, self.sample.duration)

    def unload(self):
        """Unloads the sample data from memory"""

        # Done with the streaming buffer, release references to it
        if self.sample.data.stream.map_contains_valid_sample_data:
            gst_buffer_unmap(self.sample.data.stream.buffer, &self.sample.data.stream.map_info)
            gst_sample_unref(self.sample.data.stream.sample)

            self.sample.data.stream.buffer = NULL
            self.sample.data.stream.sample = NULL
            self.sample.data.stream.map_buffer_pos = 0
            self.sample.data.stream.map_contains_valid_sample_data = 0

        # Cleanup the streaming pipeline
        gst_element_set_state(self.pipeline, GST_STATE_NULL)
        gst_object_unref(self.pipeline)

    @property
    def loaded(self):
        """Returns whether or not the sound file data is loaded in memory"""
        return self.sample.data.stream != NULL and self.sample.data.stream.pipeline != NULL and self.sample.data.stream.sink != NULL
