from kivy.graphics import Point as KivyPoint
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget
from kivy.properties import (ListProperty, NumericProperty, OptionProperty,
                             BooleanProperty)
from mpfmc.uix.widget import MpfWidget


class Point(MpfWidget, Widget):

    widget_type_name = 'Point'

    def on_pos(self, *args):
        del args

        with self.canvas:
            Color(*self.color)
            KivyPoint(points=self.points,
                      pointsize=self.pointsize)

    #
    # Properties
    #

    color = ListProperty([1.0, 1.0, 1.0, 1.0])
    '''The color of the widget lines, in the (r, g, b, a) format.

    :attr:`color` is a :class:`~kivy.properties.ListProperty` and
    defaults to [1.0, 1.0, 1.0, 1.0].
    '''

    points = ListProperty()
    '''The list of points to use to draw the widget in (x1, y1, x2, y2...)
    format.

    :attr:`points` is a :class:`~kivy.properties.ListProperty`.
    '''

    pointsize = NumericProperty(1.0)
    '''The size of the point, measured from the center to the edge. A
    value of 1.0 therefore means the real size will be 2.0 x 2.0.

    :attr:`pointsize` is a :class:`~kivy.properties.NumericProperty` and defaults
    to 1.0.
    '''


widget_classes = [Point]
