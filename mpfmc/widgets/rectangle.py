from kivy.graphics import Rectangle as KivyRectangle
from kivy.graphics import RoundedRectangle
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget

from mpfmc.core.utils import set_position
from mpfmc.uix.widget import MpfWidget


class Rectangle(MpfWidget, Widget):

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

            if self.config['corner_radius']:
                RoundedRectangle(pos=pos, size=self.size,
                                 radius=(self.config['corner_radius'],
                                         self.config['corner_radius']),
                                 segments=self.config['corner_segments'])
            else:
                KivyRectangle(pos=pos, size=self.size)
