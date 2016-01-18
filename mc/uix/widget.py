from kivy.properties import NumericProperty
from kivy.properties import ObjectProperty

from kivy.animation import Animation
from mpf.system.config import CaseInsensitiveDict


class MpfWidget(object):
    """Mixin class that's used to extend all the Kivy widget base classes with
    a few extra attributes and methods we need for everything to work with MPF.

    """
    mode = ObjectProperty(None, allownone=True)
    """:class:`Mode` object, which is the mode that created this widget."""

    config = CaseInsensitiveDict()
    """Dict which holds the settings for this widget."""

    slide = None
    """Slide that this widget will be used with."""

    def __init__(self, mc, mode, slide=None, config=None, **kwargs):
        super().__init__()

        self.mode = mode
        self.slide = slide
        self.config = config
        self.mc = mc

        if not config:
            return

        for k, v in self.config.items():
            if hasattr(self, k):
                setattr(self, k, v)

        if 'animation' in config:
            if 'entrance' in config['animation']:
                for prop, settings in config['animation']['entrance'].items():

                    if 'start' in settings:
                        if hasattr(self, prop):
                            setattr(self, prop, settings['start'])

                    anim = Animation(t=settings['function'],
                                     duration=settings['time'],
                                     **{prop: settings['end']})
                    anim.start(self)

    def __repr__(self):
        return '<{} Widget id={}>'.format(self.widget_type_name, self.id)

    def on_size(self, *args):
        try:
            self.pos = self.slide.set_position(self.slide, self,
                                                self.config['x'],
                                                self.config['y'],
                                                self.config['h_pos'],
                                                self.config['v_pos'])
        except AttributeError:
            pass
