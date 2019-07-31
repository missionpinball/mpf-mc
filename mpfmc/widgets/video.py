"""Widget showing a video."""
from typing import Optional

from kivy.uix.image import Image
from kivy.graphics import Rectangle, Color, Rotate, Scale
from kivy.properties import NumericProperty, OptionProperty, BooleanProperty, ObjectProperty

from mpfmc.uix.widget import Widget, magic_events

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc
    from mpfmc.assets.video import VideoAsset
    from kivy.graphics.texture import Texture   # noqa


class VideoWidget(Widget, Image):

    """Widget showing a video."""

    widget_type_name = 'Video'
    merge_settings = ('height', 'width')
    animation_properties = ('x', 'y')

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str] = None, **kwargs) -> None:
        del kwargs
        self._video = None  # type: VideoAsset

        video_name = config['video']
        del config['video']

        # Call base class constructors manually (super will not apply arguments correctly)
        Widget.__init__(self, mc=mc, config=config, key=key)
        Image.__init__(self)

        try:
            self._video = self.mc.videos[video_name]
        except Exception:
            raise ValueError("Cannot add Video widget. Video '{}' is not a "
                             "valid video name.".format(video_name))

        if not self._video:
            if not self.mc.asset_manager.initial_assets_loaded:
                raise ValueError("Tried to use a video '{}' when the initial asset loading run has not yet been "
                                 "completed. Try to use 'init_done' as event to show your slides if you want to "
                                 "use videos.".format(video_name))
            else:
                raise ValueError("Cannot add Video widget. Video '{}' is not a "
                                 "valid video name.".format(video_name))

        self._control_events = list()

        self._registered_magic_events = dict()
        for event in magic_events:
            self._registered_magic_events[event] = list()

        self.merge_asset_config(self._video)

        if self.config['control_events']:
            self._setup_control_events(self.config['control_events'])

        # Bind to all properties that when changed need to force
        # the widget to be redrawn
        self.bind(pos=self._draw_widget,
                  size=self._draw_widget,
                  color=self._draw_widget,
                  texture=self._draw_widget,
                  rotation=self._draw_widget,
                  scale=self._draw_widget)

        if not self._video.loaded:
            self._video.load(callback=self._on_video_loaded)
        else:
            self._on_video_loaded()

    def __repr__(self) -> str:  # pragma: no cover
        try:
            return '<Video name={}, size={}, pos={}>'.format(self._video.name,
                                                             self.size,
                                                             self.pos)
        except AttributeError:
            return '<Video (loading...), size={}, pos={}>'.format(self.size,
                                                                  self.pos)

    @property
    def video(self):
        return self._video

    def _draw_widget(self, *args):
        """Draws the image (draws a rectangle using the image texture)"""
        del args

        anchor = (self.x - self.anchor_offset_pos[0], self.y - self.anchor_offset_pos[1])
        self.canvas.clear()

        if self.state in ('play', 'pause'):
            with self.canvas:
                Color(*self.color)
                Rotate(angle=self.rotation, origin=anchor)
                Scale(self.scale).origin = anchor
                Rectangle(pos=self.pos, size=self.size, texture=self.texture)

    def _setup_control_events(self, event_list: list) -> None:
        for entry in event_list:

            kwargs = dict()

            if entry['action'] == 'play':
                handler = self.play

            elif entry['action'] == 'pause':
                handler = self.pause

            elif entry['action'] == 'stop':
                handler = self.stop

            elif entry['action'] == 'seek':
                handler = self.seek
                kwargs = {'percent': entry['value']}

            elif entry['action'] == 'volume':
                handler = self.set_volume
                kwargs = {'volume': entry['value']}

            elif entry['action'] == 'position':
                handler = self.set_playback_position
                kwargs = {'position': entry['value']}

            else:
                raise AssertionError("Invalid control_event action {} in "
                                     "video".format(entry['action']), self)

            if entry['event'] in magic_events:
                self._registered_magic_events[entry['event']].append(
                    (handler, kwargs))

            else:
                self._control_events.append(
                    self.mc.events.add_handler(entry['event'], handler,
                                               **kwargs))

    def on_add_to_slide(self, dt) -> None:
        super().on_add_to_slide(dt)
        for handler, kwargs in self._registered_magic_events['add_to_slide']:
            handler(**kwargs)

    def on_remove_from_slide(self) -> None:
        super().on_remove_from_slide()
        for handler, kwargs in self._registered_magic_events[
                'remove_from_slide']:
            handler(**kwargs)

    def on_pre_show_slide(self) -> None:
        super().on_pre_show_slide()
        for handler, kwargs in self._registered_magic_events['pre_show_slide']:
            handler(**kwargs)

    def on_show_slide(self) -> None:
        super().on_show_slide()
        for handler, kwargs in self._registered_magic_events['show_slide']:
            handler(**kwargs)

    def on_pre_slide_leave(self) -> None:
        super().on_pre_slide_leave()
        for handler, kwargs in self._registered_magic_events[
                'pre_slide_leave']:
            handler(**kwargs)

    def on_slide_leave(self) -> None:
        super().on_slide_leave()
        for handler, kwargs in self._registered_magic_events['slide_leave']:
            handler(**kwargs)

    def on_slide_play(self) -> None:
        super().on_slide_play()
        for handler, kwargs in self._registered_magic_events['slide_play']:
            handler(**kwargs)

    def play(self, **kwargs) -> None:
        del kwargs
        if not self._video.loaded:
            return
        self.state = 'play'

    def pause(self, **kwargs) -> None:
        del kwargs
        if not self._video.loaded:
            return
        self.state = 'pause'

    def stop(self, **kwargs) -> None:
        del kwargs
        if not self._video.loaded:
            return
        self.state = 'stop'

    def seek(self, percent, **kwargs) -> None:
        """Change the position to a percentage of duration.

        :Parameters:
            `percent`: float or int
                Position to seek, must be between 0-1.

        .. warning::
            Calling seek() before the video is loaded has no effect.

        """
        del kwargs
        if not self._video.loaded:
            raise Exception('Video not loaded.')
        self._video.video.seek(percent)

    def set_volume(self, volume, **kwargs) -> None:
        del kwargs
        if not self._video.loaded:
            return
        self.volume = volume

    def set_playback_position(self, position: float, **kwargs) -> None:
        del kwargs
        if not self._video.loaded:
            return
        self._video.video.seek(position / self.duration)

    def _on_video_loaded(self, *largs) -> None:
        """Called after the video asset has been loaded. Initializes the widget in preparation
        for displaying the video.
        """
        del largs

        self.volume = self.config['volume']
        if self.config['auto_play']:
            self.state = 'play'
        else:
            self.state = 'stop'

        if self._video.loaded:
            self._video.video.stop()

        if self._video.loaded:
            self._video.volume = self.volume
            self._video.video.bind(on_load=self._on_load,
                                   on_frame=self._on_video_frame,
                                   on_eos=self._on_eos)

            if self.state == 'play':
                self._video.video.play()
            self.duration = 1.

            self._video.set_end_behavior(self.config['end_behavior'])
        else:
            raise(Exception("Video player could not be loaded"))

    def _on_video_frame(self, *largs):
        """Callback whenever a new video frame arrives"""
        del largs
        video = self._video
        if not video:
            return
        self.duration = video.duration
        self.position = video.position
        self.texture = video.texture
        self.canvas.ask_update()

    def _on_eos(self, *largs):
        del largs
        if self._video.video.eos != 'loop':
            self.state = 'stop'
            self.eos = True

    def _on_load(self, *largs):
        self.loaded = True
        if self._video.texture is not None:
            if self.config['width'] and self.config['height']:
                self.size = (self.config['width'], self.config['height'])
            else:
                self.size = list(self._video.texture.size)

        self._on_video_frame(largs)

    def on_state(self, instance, value):
        del instance
        if not self._video:
            return
        if value == 'play':
            if self.eos:
                self._video.video.stop()
                self._video.video.position = 0.
            self.eos = False
            self._video.video.play()
        elif value == 'pause':
            self._video.video.pause()
        else:
            self._video.video.stop()
            self._video.video.position = 0

    def on_volume(self, instance, value):
        del instance
        if self._video:
            self._video.video.volume = value

    def unload(self):
        """Unload the video. The playback will be stopped."""
        if self._video and self._video.video:
            self._video.video.stop()
            self._video.video.unload()
            self._video = None
        self.loaded = False

    def prepare_for_removal(self) -> None:
        super().prepare_for_removal()
        self.mc.events.remove_handlers_by_keys(self._control_events)
        self._control_events = list()
        self.stop()

    #
    # Properties
    #

    rotation = NumericProperty(0)
    '''Rotation angle value of the widget.

    :attr:`rotation` is an :class:`~kivy.properties.NumericProperty` and defaults to
    0.
    '''

    scale = NumericProperty(1.0)
    '''Scale value of the widget.

    :attr:`scale` is an :class:`~kivy.properties.NumericProperty` and defaults to
    1.0.
    '''

    state = OptionProperty('stop', options=('play', 'pause', 'stop'))
    '''String, indicates whether to play, pause, or stop the video::

        # start playing the video at creation
        video = Video(source='movie.mkv', state='play')

        # create the video, and start later
        video = Video(source='movie.mkv')
        # and later
        video.state = 'play'

    :attr:`state` is an :class:`~kivy.properties.OptionProperty` and defaults
    to 'stop'.
    '''

    eos = BooleanProperty(False)
    '''Boolean, indicates whether the video has finished playing or not
    (reached the end of the stream).

    :attr:`eos` is a :class:`~kivy.properties.BooleanProperty` and defaults to
    False.
    '''

    loaded = BooleanProperty(False)
    '''Boolean, indicates whether the video is loaded and ready for playback
    or not.

    :attr:`loaded` is a :class:`~kivy.properties.BooleanProperty` and defaults
    to False.
    '''

    position = NumericProperty(-1)
    '''Position of the video between 0 and :attr:`duration`. The position
    defaults to -1 and is set to a real position when the video is loaded.

    :attr:`position` is a :class:`~kivy.properties.NumericProperty` and
    defaults to -1.
    '''

    duration = NumericProperty(-1)
    '''Duration of the video. The duration defaults to -1, and is set to a real
    duration when the video is loaded.

    :attr:`duration` is a :class:`~kivy.properties.NumericProperty` and
    defaults to -1.
    '''

    volume = NumericProperty(1.)
    '''Volume of the video, in the range 0-1. 1 means full volume, 0
    means mute.

    :attr:`volume` is a :class:`~kivy.properties.NumericProperty` and defaults
    to 1.
    '''

    options = ObjectProperty({})
    '''Options to pass at Video core object creation.

    :attr:`options` is an :class:`kivy.properties.ObjectProperty` and defaults
    to {}.
    '''


widget_classes = [VideoWidget]
