from kivy.graphics import Line as KivyLine
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget
from mpfmc.uix.widget import MpfWidget


class Line(MpfWidget, Widget):

    widget_type_name = 'Line'

    def __init__(self, mc, config, slide, key=None, **kwargs):
        super().__init__(mc=mc, slide=slide, config=config, key=key)

        with self.canvas:
            Color(*self.config['color'])
            KivyLine(points=self.config['points'],
                     width=self.config['thickness'],
                     cap=self.config['cap'],
                     joint=self.config['joint'],
                     cap_precision=self.config['cap_precision'],
                     joint_precision=self.config['joint_precision'],
                     close=self.config['close'])
