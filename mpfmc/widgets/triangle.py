from kivy.graphics import Triangle as KivyTriangle
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget
from mpfmc.uix.widget import MpfWidget


class Triangle(MpfWidget, Widget):

    widget_type_name = 'Triangle'

    def __init__(self, mc, config, slide, mode=None, priority=None, **kwargs):
        super().__init__(mc=mc, mode=mode, priority=priority, slide=slide,
                         config=config)

        with self.canvas:
            Color(*self.config['color'])
            KivyTriangle(points=self.config['points'])
