from kivy.graphics import Point as KivyPoint
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget
from mpfmc.uix.widget import MpfWidget


class Point(MpfWidget, Widget):

    widget_type_name = 'Point'

    def on_pos(self, *args):
        del args

        with self.canvas:
            Color(*self.config['color'])
            KivyPoint(points=self.config['points'],
                      pointsize=self.config['pointsize'])
