from kivy.graphics import Quad as KivyQuad
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget
from mpfmc.uix.widget import MpfWidget


class Quad(MpfWidget, Widget):

    widget_type_name = 'Quad'

    def __init__(self, mc, config, slide, mode=None, priority=None, key=None,
                 **kwargs):
        super().__init__(mc=mc, mode=mode, slide=slide, config=config,
                         priority=priority, key=key)

        with self.canvas:
            Color(*self.config['color'])
            KivyQuad(points=self.config['points'])
