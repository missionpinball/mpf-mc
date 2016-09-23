from kivy.graphics import Triangle as KivyTriangle
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget
from mpfmc.uix.widget import MpfWidget


class Triangle(MpfWidget, Widget):

    widget_type_name = 'Triangle'

    def on_pos(self, *args):
        del args

        with self.canvas:
            Color(*self.config['color'])
            KivyTriangle(points=self.config['points'])
