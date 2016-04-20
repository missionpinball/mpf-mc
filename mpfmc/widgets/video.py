from kivy.uix.video import Video
from kivy.core.video import Video as CoreVideo

from mpfmc.uix.widget import MpfWidget


class VideoWidget(MpfWidget, Video):
    widget_type_name = 'Video'
    merge_settings = ('height', 'width')

    def __init__(self, mc, config, slide, mode=None, priority=None, key=None,
                 **kwargs):
        super().__init__(mc=mc, mode=mode, slide=slide, config=config,
                         priority=priority, key=key)

        try:
            self.video = self.mc.videos[self.config['video']]
        except:
            raise ValueError("Cannot add Video widget. Video '{}' is not a "
                             "valid video name.".format(self.config['video']))

        self.merge_asset_config(self.video)

        # Set it to (0,0) while it's loading so we don't see a white
        # box on the slide
        self.size = (0,0)

        if not self.video.video:
            self.video.load(callback=self._do_video_load)
        else:
            self._do_video_load()

    def __repr__(self):  # pragma: no cover
        try:
            return '<Video name={}, size={}, pos={}>'.format(self.video.name,
                                                             self.size,
                                                             self.pos)
        except AttributeError:
            return '<Video (loading...), size={}, pos={}>'.format(self.size,
                                                                  self.pos)

    def _do_video_load(self, *largs):
        # Overrides a method in the base Kivy Video widget. It's basically
        # copied and pasted from there, with the change that this method pulls
        # the video object from the MPF asset versus loading from a file and
        # it has the extra bit at the end to set the size and position

        del largs

        if CoreVideo is None:
            raise TypeError("Could not find a video provider to play back "
                            "the video '{}'".format(self.video.file))

        # pylint: disable=E0203
        # Disable the error about accessing an attribute before its defined.
        # self._video is defined in the base class, but not in a direct way, so
        # pylint doesn't see it.
        if self._video:
            self._video.stop()
        elif self.video.video:
            self._video = self.video.video
            self._video.volume = self.volume
            self._video.bind(on_load=self._on_load,
                             on_frame=self._on_video_frame,
                             on_eos=self._on_eos)
            # This is also flagged as an error by pylint, but it's okay because
            # self.state is defined in the base class.
            if self.state == 'play' or self.play:
                self._video.play()
            self.duration = 1.
            self.position = 0.

            self.state = 'play'

    def on_texture(self, instance, value):
        # Overrides the base method to put the size into self.size instead of
        # self.texture_size
        del instance

        if value is not None:
            if self.config['width'] and self.config['height']:
                self.size = (self.config['width'], self.config['height'])
            else:
                self.size = list(value.size)
