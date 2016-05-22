from kivy.uix.video import Video
from kivy.core.video import Video as CoreVideo

from mpfmc.uix.widget import MpfWidget


class VideoWidget(MpfWidget, Video):
    widget_type_name = 'Video'
    merge_settings = ('height', 'width')

    def __init__(self, mc, config, slide, key=None, **kwargs):
        super().__init__(mc=mc, slide=slide, config=config, key=key)

        try:
            self.video = self.mc.videos[self.config['video']]
        except:
            raise ValueError("Cannot add Video widget. Video '{}' is not a "
                             "valid video name.".format(self.config['video']))

        self._control_events = list()

        self.merge_asset_config(self.video)

        # Set it to (0, 0) while it's loading so we don't see a white
        # box on the slide
        self.size = (0, 0)

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

    def _register_control_events(self):
        # todo should this be moved to the base widget class?

        for event in self.config['play_events']:
            self._control_events.append(
                self.machine.events.add_handler(event, self.play))

        for event in self.config['pause_events']:
            self._control_events.append(
                self.machine.events.add_handler(event, self.pause))

        for event in self.config['stop_events']:
            self._control_events.append(
                self.machine.events.add_handler(event, self.stop))

        for percent, event in self.config['seek_events'].items():
            self._control_events.append(
                self.machine.events.add_handler(event, self.seek,
                                                percent=percent))

        for volume, event in self.config['volume_events'].items():
            self._control_events.append(
                self.machine.events.add_handler(event, self.set_volume,
                                                volume=volume))

        for position, event in self.config['position_events'].items():
            self._control_events.append(
                self.machine.events.add_handler(event, self.set_position,
                                                position=position))

    def play(self, **kwargs):
        del kwargs
        self.video.play()

    def pause(self, **kwargs):
        del kwargs
        self.video.pause()

    def stop(self, **kwargs):
        del kwargs
        self.video.stop()

    def seek(self, percent, **kwargs):
        del kwargs
        super().seek(percent)

    def set_volume(self, volume, **kwargs):
        del kwargs
        self.volume = volume

    def set_position(self, position, **kwargs):
        del kwargs
        super().seek(position / self.duration)

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

    def prepare_for_removal(self, widget):
        super().prepare_for_removal(widget)
        del widget

        self.mc.events.remove_handler_by_keys(self._control_events)
        self._control_events = list()
