from kivy.graphics.vertex_instructions import Ellipse as KivyEllipse
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget

from mpfmc.core.utils import set_position
from mpfmc.uix.widget import MpfWidget


class Ellipse(MpfWidget, Widget):

    widget_type_name = 'Rectangle'

    def __init__(self, mc, config, slide, mode=None, priority=None, **kwargs):
        super().__init__(mc=mc, mode=mode, priority=priority, slide=slide,
                         config=config)

        pos = set_position(slide.width,
                           slide.height,
                           self.width, self.height,
                           self.config['x'],
                           self.config['y'],
                           self.config['anchor_x'],
                           self.config['anchor_y'])

        with self.canvas:
            Color(*self.config['color'])
            KivyEllipse(pos=pos, size=self.size,
                        segments=self.config['segments'],
                        angle_start=self.config['angle_start'],
                        angle_end=self.config['angle_end'])


