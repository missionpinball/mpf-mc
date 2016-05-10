from kivy.graphics.vertex_instructions import Ellipse as KivyEllipse
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget

from mpfmc.core.utils import set_position
from mpfmc.uix.widget import MpfWidget


class Ellipse(MpfWidget, Widget):

    widget_type_name = 'Rectangle'

    def __init__(self, mc, config, slide, key=None, **kwargs):
        super().__init__(mc=mc, slide=slide, config=config, key=key)

        pos = set_position(slide.width,
                           slide.height,
                           self.width, self.height,
                           self.config['x'],
                           self.config['y'],
                           self.config['anchor_x'],
                           self.config['anchor_y'],
                           self.config['adjust_top'],
                           self.config['adjust_right'],
                           self.config['adjust_bottom'],
                           self.config['adjust_left'])

        with self.canvas:
            Color(*self.config['color'])
            KivyEllipse(pos=pos, size=self.size,
                        segments=self.config['segments'],
                        angle_start=self.config['angle_start'],
                        angle_end=self.config['angle_end'])
