from typing import TYPE_CHECKING, Optional
from kivy.graphics import Point as KivyPoint
from kivy.graphics.context_instructions import Color, Rotate, Scale, PushMatrix, PopMatrix
from kivy.uix.widget import Widget
from kivy.properties import ListProperty, NumericProperty
from mpfmc.uix.widget import MpfWidget
from mpfmc.core.utils import center_of_points_list

if TYPE_CHECKING:
    from mpfmc.core.mc import MpfMc


class Point(MpfWidget, Widget):

    widget_type_name = 'Point'
    animation_properties = ('points', 'pointsize', 'color', 'opacity', 'rotation', 'scale')

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str]=None, **kwargs) -> None:
        del kwargs
        super().__init__(mc=mc, config=config, key=key)
        self._draw_widget()

    def _draw_widget(self) -> None:
        """Establish the drawing instructions for the widget."""
        center = center_of_points_list(self.points)
        self.canvas.clear()
        with self.canvas.before:
            PushMatrix()
        with self.canvas:
            Color(*self.color)
            Scale(self.scale, origin=center)
            Rotate(angle=self.rotation, origin=center)
            KivyPoint(points=self.points,
                      pointsize=self.pointsize)
        with self.canvas.after:
            PopMatrix()

    def on_color(self, *args):
        del args
        self._draw_widget()

    def on_points(self, *args):
        del args
        self._draw_widget()

    def on_pointsize(self, *args):
        del args
        self._draw_widget()

    def on_rotation(self, *args):
        del args
        self._draw_widget()

    def on_scale(self, *args):
        del args
        self._draw_widget()

    #
    # Properties
    #

    color = ListProperty([1.0, 1.0, 1.0, 1.0])
    '''The color of the widget lines, in the (r, g, b, a) format.

    :attr:`color` is a :class:`~kivy.properties.ListProperty` and
    defaults to [1.0, 1.0, 1.0, 1.0].
    '''

    points = ListProperty([100, 100])
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

    rotation = NumericProperty(0)
    '''Rotation angle value of the widget.

    :attr:`rotation` is an :class:`~kivy.properties.NumericProperty` and defaults to
    0.
    '''

    scale = NumericProperty(1.0)
    '''Scale value of the widget.

    :attr:`scale` is an :class:`~kivy.properties.NumericProperty` and defaults to
    1.0.
    '''

widget_classes = [Point]
