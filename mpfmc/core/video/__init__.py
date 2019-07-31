
__all__ = ('Video', 'GstVideo', 'get_gst_version')

from mpfmc.core.video.gst_video import GstVideo, get_gst_version

from kivy.event import EventDispatcher
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from threading import Lock
from functools import partial
from weakref import ref
from urllib.request import pathname2url
from os.path import realpath
import logging


def _on_gst_video_buffer(video, width, height, data):
    video = video()
    # if we still receive the video but no more player, remove it.
    if not video:
        return
    with video._buffer_lock:
        video._buffer = (width, height, data)


def _on_gst_video_message(mtype, message):
    log = logging.getLogger('Video')
    if mtype == 'error':
        log.error('Video: GstVideo - {}'.format(message))
    elif mtype == 'warning':
        log.warning('Video: GstVideo - {}'.format(message))
    elif mtype == 'info':
        log.info('Video: GstVideo - {}'.format(message))


class Video(EventDispatcher):
    """Load a video and store the size and texture.

    :Parameters:
        `uri`: A string path to the image file or data URI to be loaded.
        `alpha_channel`: bool, defaults to False
            Keep the image data when the texture is created.
    """

    def __init__(self, filename, alpha_channel=False, **kwargs):
        self.log = logging.getLogger('Video')
        self.log.debug('Video: Using Gstreamer {}'.format('.'.join(map(str, get_gst_version()))))

        self.register_event_type('on_load')
        self.register_event_type('on_unload')
        self.register_event_type('on_frame')
        self.register_event_type('on_play')
        self.register_event_type('on_stop')
        self.register_event_type('on_eos')

        kwargs.setdefault('eos', 'stop')
        kwargs.setdefault('autoplay', False)

        super(Video, self).__init__()

        self._state = ''
        self._alpha_channel = alpha_channel
        self._filename = filename
        self._size = [0, 0]
        self._gst_video = None
        self._texture = None
        self._frame_callback = None
        self._buffer = None
        self._buffer_lock = Lock()
        self._volume = 1.
        self._framerate = kwargs.get('framerate', 30.)
        self.eos = kwargs.get('eos', 'stop')

        if self._alpha_channel:
            self._colorfmt = 'rgba'
        else:
            self._colorfmt = 'rgb'
            
        self._texture_update_clock = None

    def _on_gst_eos_sync(self):
        """Thread-safe method to trigger video eos behavior"""
        Clock.schedule_once(self._do_eos, 0)

    def load(self):
        """Load the video and create the Gstreamer video playback class"""
        self.log.debug('Video: Load <{}>'.format(self._filename))
        wk_self = ref(self)
        self._frame_callback = partial(_on_gst_video_buffer, wk_self)
        self._gst_video = GstVideo(self.uri,
                                   self._frame_callback,
                                   self._on_gst_eos_sync,
                                   _on_gst_video_message,
                                   self._alpha_channel)
        self._gst_video.load()

    def unload(self):
        """Unload the video and clean-up playback resources"""
        self._state = ''

        # Stop the texture callback clock
        if self._texture_update_clock:
            self._texture_update_clock.cancel()
            self._texture_update_clock = None

        if self._gst_video:
            self._gst_video.unload()
            self._gst_video = None

        with self._buffer_lock:
            self._buffer = None

        self._texture = None
        self.dispatch('on_unload')

    def _do_eos(self, *args):
        """Called when the video reaches eos"""
        self.dispatch('on_eos')

        # Determine next action
        if self.eos == 'pause':
            self.pause()
        elif self.eos == 'stop':
            self.stop()
        elif self.eos == 'loop':
            self.position = 0
            self.play()

    def _update(self, dt):
        """
        Update the texture with video buffer data.  Callback function called at the specified
         framerate by the Kivy clock.
        Args:
            dt: Delta time since last callback
        """
        del dt

        buf = None
        with self._buffer_lock:
            buf = self._buffer
            self._buffer = None

        if buf is not None:
            width, height, data = buf

            # texture is not allocated yet, create it first
            if not self._texture:
                self._texture = Texture.create(size=(width, height), colorfmt=self._colorfmt)
                self._texture.flip_vertical()
                self.dispatch('on_load')

            if self._texture:
                self._texture.blit_buffer(data, size=(width, height), colorfmt=self._colorfmt)

            self.dispatch('on_frame')

    def _get_video(self):
        return self._gst_video

    video = property(_get_video, None, doc='Get the underlying GstVideo object')

    def _get_filename(self):
        return self._filename

    filename = property(_get_filename, None, doc='Get the filename of the video')

    def _get_uri(self):
        uri = self.filename
        if not uri:
            return
        if '://' not in uri:
            uri = 'file:' + pathname2url(realpath(uri))
        return uri

    uri = property(_get_uri, None, doc='Get the URI of the video')

    def _get_position(self):
        if self._gst_video:
            return self._gst_video.get_position()
        else:
            return 0

    def _set_position(self, pos):
        self.seek(pos)

    position = property(lambda self: self._get_position(),
                        lambda self, x: self._set_position(x),
                        doc='Get/set the position in the video (in seconds)')

    def _get_volume(self):
        return self._volume

    def _set_volume(self, volume):
        self._volume = volume
        if self._gst_video:
            self._gst_video.set_volume(self._volume)

    volume = property(lambda self: self._get_volume(),
                      lambda self, x: self._set_volume(x),
                      doc='Get/set the volume in the video (1.0 = 100%)')

    def _get_duration(self):
        if self._gst_video:
            return self._gst_video.get_duration()
        else:
            return 0

    duration = property(lambda self: self._get_duration(),
                        doc='Get the video duration (in seconds)')

    def _get_state(self):
        return self._state

    state = property(lambda self: self._get_state(), doc='Get the video playing status')

    def _get_texture(self):
        return self._texture

    texture = property(lambda self: self._get_texture(), doc='Get the video texture')

    @property
    def size(self):
        """Video size (width, height)"""
        return self._size

    @property
    def width(self):
        """Video width"""
        return self._size[0]

    @property
    def height(self):
        """Image height"""
        return self._size[1]

    def stop(self):
        """Stops the video playing"""
        self._state = ''
        if self._gst_video:
            self._gst_video.stop()
            self.dispatch('on_stop')

            # Stop the texture callback clock (no need to update texture when video is stopped)
            if self._texture_update_clock:
                self._texture_update_clock.cancel()
                self._texture_update_clock = None

    def pause(self):
        """Pauses the video"""
        if self._gst_video:
            self._state = 'paused'
            self._gst_video.pause()

    def play(self):
        """Plays the video"""
        if self._gst_video:
            self._state = 'playing'
            # Start the texture callback clock (updates the texture at the specified framerate)
            if not self._texture_update_clock:
                self._texture_update_clock = Clock.schedule_interval(self._update, 1 / self._framerate)

            self._gst_video.set_volume(self.volume)
            self._gst_video.play()
            self.dispatch('on_play')

    def seek(self, percent):
        if self._gst_video:
            self._gst_video.seek(percent)

    def on_load(self):
        pass

    def on_unload(self):
        pass

    def on_frame(self):
        pass

    def on_eos(self):
        pass

    def on_play(self):
        pass

    def on_stop(self):
        pass
