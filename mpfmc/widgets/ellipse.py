from kivy.graphics.vertex_instructions import Ellipse as KivyEllipse
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget

from mpfmc.core.utils import set_position
from mpfmc.uix.widget import MpfWidget


class Ellipse(MpfWidget, Widget):

    widget_type_name = 'Ellipse'

    def on_pos(self, *args):
        del args

        self.pos = set_position(self.parent.width,
                                self.parent.height,
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
            KivyEllipse(pos=self.pos, size=self.size,
                        segments=self.config['segments'],
                        angle_start=self.config['angle_start'],
                        angle_end=self.config['angle_end'])
