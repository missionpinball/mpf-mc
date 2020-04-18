from kivy.core.video import Video
from kivy.core.video.video_null import VideoNull
from kivy.properties import AliasProperty

from mpf.core.assets import AssetPool
from mpfmc.assets.mc_asset import McAsset


class VideoPool(AssetPool):

    def __repr__(self):
        return '<VideoPool: {}>'.format(self.name)

    @property
    def video(self):
        return self.asset


class VideoWrapper(Video):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_event_type('on_play')
        self.register_event_type('on_stop')

    def on_play(self):
        pass

    def on_stop(self):
        pass

    def stop(self):
        super().stop()
        self.dispatch('on_stop')

    def play(self):
        super().play()
        self.dispatch('on_play')


class VideoAsset(McAsset):

    attribute = 'videos'
    path_string = 'videos'
    config_section = 'videos'
    extensions = ('mkv', 'avi', 'mpg', 'mp4', 'm4v', 'mov')
    class_priority = 100
    pool_config_section = 'video_pools'
    asset_group_class = VideoPool

    def __init__(self, mc, name, file, config):
        self._video = None      # type: VideoWrapper
        super().__init__(mc, name, file, config)

        # Setup events to post when video state changes
        self._events_when_played = list()
        self._events_when_stopped = list()

        if self.config['events_when_played']:
            self._events_when_played = self.config['events_when_played']

        if self.config['events_when_stopped']:
            self._events_when_stopped = self.config['events_when_stopped']

    @property
    def video(self):
        return self._video

    def do_load(self):
        # For videos, we need them to load in the main thread, so we do not
        # load them here and load them via is_loaded() below.
        pass

    def _do_unload(self):
        if self._video:
            self._video.stop()
            self._video.unload()
            self._video = None

    def set_end_behavior(self, eos='stop'):
        assert eos in ('loop', 'pause', 'stop')
        self._video.eos = eos

    def is_loaded(self):
        self.loading = False
        self.loaded = True
        self.unloading = False
        self._video = VideoWrapper(filename=self.file)
        self._video.bind(on_load=self._check_duration,
                         on_play=self.on_play,
                         on_stop=self.on_stop)

        if isinstance(self._video, VideoNull):
            raise AssertionError("Kivy cannot load video {} because there is no provider.".format(self.file))

        self._call_callbacks()

    def _check_duration(self, instance):
        del instance
        if self._video and self._video.duration <= 0:
            raise ValueError(
                "Video file {} was loaded, but seems to have no content. Check"
                " to make sure you have the proper Gstreamer plugins for the "
                "codec this video needs".format(self.file))

    def on_play(self, *args):
        del args

        if self._events_when_played:
            for event in self._events_when_played:
                self.machine.post_mc_native_event(event)

    def on_stop(self, *args):
        del args

        if self._events_when_stopped:
            for event in self._events_when_stopped:
                self.machine.post_mc_native_event(event)

    #
    # Properties
    #

    def _get_position(self):
        try:
            return self._video.position
        except AttributeError:
            return 0

    def _set_position(self, pos):
        # position in secs
        try:
            self._video.position = pos  # noqa
        except AttributeError:
            pass

    position = AliasProperty(_get_position, _set_position)
    '''Position of the video between 0 and :attr:`duration`. The position
    defaults to -1 and is set to a real position when the video is loaded.

    :attr:`position` is a :class:`~kivy.properties.NumericProperty` and
    defaults to -1.
    '''

    def _get_duration(self):
        try:
            return self._video.duration
        except AttributeError:
            return 0

    duration = AliasProperty(_get_duration, None)
    '''Duration of the video. The duration defaults to -1, and is set to a real
    duration when the video is loaded.

    :attr:`duration` is a :class:`~kivy.properties.NumericProperty` and
    defaults to -1.
    '''

    def _get_volume(self):
        try:
            return self._video.volume
        except AttributeError:
            return 0

    def _set_volume(self, volume):
        # float 0.0 - 1.0
        try:
            self._video.volume = volume     # noqa
        except AttributeError:
            pass

    volume = AliasProperty(_get_volume, _set_volume)
    '''Volume of the video, in the range 0-1. 1 means full volume, 0
    means mute.

    :attr:`volume` is a :class:`~kivy.properties.NumericProperty` and defaults
    to 1.
    '''

    def _get_state(self):
        return self._video.state

    state = AliasProperty(_get_state, None)
    '''String, indicates whether to play, pause, or stop the video::
    '''
