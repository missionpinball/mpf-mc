from kivy.graphics import Line as KivyLine
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget
from mpfmc.uix.widget import MpfWidget


class Line(MpfWidget, Widget):

    widget_type_name = 'Line'

    def on_pos(self, *args):
        del args

        with self.canvas:
            Color(*self.config['color'])
            KivyLine(points=self.config['points'],
                     width=self.config['thickness'],
                     cap=self.config['cap'],
                     joint=self.config['joint'],
                     cap_precision=self.config['cap_precision'],
                     joint_precision=self.config['joint_precision'],
                     close=self.config['close'])
