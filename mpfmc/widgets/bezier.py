from kivy.graphics import Line as KivyLine
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget
from mpfmc.uix.widget import MpfWidget


class Bezier(MpfWidget, Widget):

    widget_type_name = 'Bezier'

    def __init__(self, mc, config, key=None, **kwargs):
        super().__init__(mc=mc, config=config, key=key)

        with self.canvas:
            Color(*self.config['color'])
            KivyLine(bezier=self.config['points'],
                     width=self.config['thickness'],
                     cap=self.config['cap'],
                     joint=self.config['joint'],
                     cap_precision=self.config['cap_precision'],
                     joint_precision=self.config['joint_precision'],
                     close=self.config['close'],
                     bezier_precision=self.config['precision'])
