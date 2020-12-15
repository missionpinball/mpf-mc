"""Widget showing a point."""
from typing import Optional

from kivy.graphics import Point as KivyPoint
from kivy.graphics.context_instructions import Color, Rotate, Scale
from kivy.properties import ListProperty, NumericProperty

from mpfmc.uix.widget import Widget
from mpfmc.core.utils import center_of_points_list

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc     # pylint: disable-msg=cyclic-import,unused-import


class Point(Widget):

    """Widget showing a point."""

    widget_type_name = 'Point'
    animation_properties = ('points', 'pointsize', 'color', 'opacity', 'rotation', 'scale')

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str] = None, **kwargs) -> None:
        del kwargs
        super().__init__(mc=mc, config=config, key=key)

        # The points in this widget are always relative to the bottom left corner
        self.anchor_pos = ("left", "bottom")

        # Bind to all properties that when changed need to force
        # the widget to be redrawn
        self.bind(color=self._draw_widget,
                  points=self._draw_widget,
                  pointsize=self._draw_widget,
                  rotation=self._draw_widget,
                  scale=self._draw_widget)

        self._draw_widget()

    def _draw_widget(self, *args) -> None:
        """Establish the drawing instructions for the widget."""
        del args

        if self.canvas is None:
            return

        # TODO: allow user to set rotation/scale origin
        center = center_of_points_list(self.points)
        self.canvas.clear()

        with self.canvas:
            Color(*self.color)
            Scale(self.scale, origin=center)
            Rotate(angle=self.rotation, origin=center)
            KivyPoint(points=self.points,
                      pointsize=self.pointsize)

    #
    # Properties
    #

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
