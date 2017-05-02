from kivy.graphics import Quad as KivyQuad
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget
from kivy.properties import ListProperty
from mpfmc.uix.widget import MpfWidget


class Quad(MpfWidget, Widget):

    widget_type_name = 'Quad'

    def on_pos(self, *args):
        del args

        with self.canvas:
            Color(*self.color)
            KivyQuad(points=self.points)

    #
    # Properties
    #

    color = ListProperty([1.0, 1.0, 1.0, 1.0])
    '''The color of the widget lines, in the (r, g, b, a) format.

    :attr:`color` is a :class:`~kivy.properties.ListProperty` and
    defaults to [1.0, 1.0, 1.0, 1.0].
    '''

    points = ListProperty()
    '''The list of points to use to draw the widget in (x1, y1, x2, y2,
    x3, y3, x4, y4) format.

    :attr:`points` is a :class:`~kivy.properties.ListProperty`.
    '''

widget_classes = [Quad]
