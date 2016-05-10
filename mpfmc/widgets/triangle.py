from kivy.graphics import Triangle as KivyTriangle
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget
from mpfmc.uix.widget import MpfWidget


class Triangle(MpfWidget, Widget):

    widget_type_name = 'Triangle'

    def __init__(self, mc, config, slide, key=None, **kwargs):
        super().__init__(mc=mc, slide=slide, config=config, key=key)

        with self.canvas:
            Color(*self.config['color'])
            KivyTriangle(points=self.config['points'])
