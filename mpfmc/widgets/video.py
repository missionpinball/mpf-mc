from kivy.uix.video import Video
from kivy.core.video import Video as CoreVideo

from mpfmc.uix.widget import MpfWidget, magic_events


class VideoWidget(MpfWidget, Video):
    widget_type_name = 'Video'
    merge_settings = ('height', 'width')

    def __init__(self, mc, config, key=None, **kwargs):
        super().__init__(mc=mc, config=config, key=key)

        try:
            self.video = self.mc.videos[self.config['video']]
        except:
            raise ValueError("Cannot add Video widget. Video '{}' is not a "
                             "valid video name.".format(self.config['video']))

        self._control_events = list()

        self._registered_magic_events = dict()
        for event in magic_events:
            self._registered_magic_events[event] = list()

        self.merge_asset_config(self.video)

        # Set it to (0, 0) while it's loading so we don't see a white
        # box on the slide
        self.size = (0, 0)

        if self.config['control_events']:
            self._setup_control_events(self.config['control_events'])

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

    def _setup_control_events(self, event_list):
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
                handler = self.set_position
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

    def on_add_to_slide(self, dt):
        super().on_add_to_slide(dt)
        for handler, kwargs in self._registered_magic_events['add_to_slide']:
            handler(**kwargs)

    def on_remove_from_slide(self):
        super().on_remove_from_slide()
        for handler, kwargs in self._registered_magic_events[
                'remove_from_slide']:
            handler(**kwargs)

    def on_pre_show_slide(self):
        super().on_pre_show_slide()
        for handler, kwargs in self._registered_magic_events['pre_show_slide']:
            handler(**kwargs)

    def on_show_slide(self):
        super().on_show_slide()
        for handler, kwargs in self._registered_magic_events['show_slide']:
            handler(**kwargs)

    def on_pre_slide_leave(self):
        super().on_pre_slide_leave()
        for handler, kwargs in self._registered_magic_events[
                'pre_slide_leave']:
            handler(**kwargs)

    def on_slide_leave(self):
        super().on_slide_leave()
        for handler, kwargs in self._registered_magic_events['slide_leave']:
            handler(**kwargs)

    def on_slide_play(self):
        super().on_slide_play()
        for handler, kwargs in self._registered_magic_events['slide_play']:
            handler(**kwargs)

    def play(self, **kwargs):
        del kwargs
        self.video.play()
        self.state = 'play'

    def pause(self, **kwargs):
        del kwargs
        self.video.pause()
        self.state = 'pause'

    def stop(self, **kwargs):
        del kwargs
        self.video.stop()
        self.state = 'stop'

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

        self.volume = self.config['volume']
        if self.config['auto_play']:
            self.state = 'play'
        else:
            self.state = 'stop'

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

            if self.state == 'play':
                self._video.play()
            self.duration = 1.

        self.video.set_end_behavior(self.config['end_behavior'])

    def on_texture(self, instance, value):
        # Overrides the base method to put the size into self.size instead of
        # self.texture_size
        del instance

        if value is not None:
            if self.config['width'] and self.config['height']:
                self.size = (self.config['width'], self.config['height'])
            else:
                self.size = list(value.size)

    def prepare_for_removal(self):
        super().prepare_for_removal()
        self.mc.events.remove_handlers_by_keys(self._control_events)
        self._control_events = list()
        self.stop()
