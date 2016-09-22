from kivy.graphics import Quad as KivyQuad
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget
from mpfmc.uix.widget import MpfWidget


class Quad(MpfWidget, Widget):

    widget_type_name = 'Quad'

    def on_pos(self, *args):
        del args

        with self.canvas:
            Color(*self.config['color'])
            KivyQuad(points=self.config['points'])
