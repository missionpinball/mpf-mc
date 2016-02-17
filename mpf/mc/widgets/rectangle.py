from kivy.graphics import Rectangle as KivyRectangle
from kivy.graphics import RoundedRectangle
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget

from mpf.mc.core.utils import set_position
from mpf.mc.uix.widget import MpfWidget


class Rectangle(MpfWidget, Widget):

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

            if self.config['corner_radius']:
                RoundedRectangle(pos=pos, size=self.size,
                                 radius=(self.config['corner_radius'],
                                         self.config['corner_radius']),
                                 segments=self.config['corner_segments'])
            else:
                KivyRectangle(pos=pos, size=self.size)
