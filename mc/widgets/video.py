from kivy.uix.video import Video

from mc.uix.widget import MpfWidget


class VideoWidget(MpfWidget, Video):
    widget_type_name = 'Video'

    def __init__(self, mc, config, slide, mode=None, priority=None):
        super().__init__(mc=mc, mode=mode, priority=priority, slide=slide,
                         config=config)

        self.source = self.mc.videos[self.config['video']].config['file']

    def __repr__(self):  # pragma: no cover
        try:
            return '<Video name={}, size={}, pos={}>'.format(self.video.name,
                                                             self.size,
                                                             self.pos)
        except AttributeError:
            return '<Video (loading...), size={}, pos={}>'.format(self.size,
                                                                  self.pos)

