"""Widget showing a quad."""
from typing import Optional

from kivy.graphics import Quad as KivyQuad
from kivy.graphics.context_instructions import Color, Rotate, Scale
from kivy.properties import ListProperty, NumericProperty

from mpfmc.uix.widget import Widget
from mpfmc.core.utils import center_of_points_list

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc     # pylint: disable-msg=cyclic-import,unused-import


class Quad(Widget):

    """Widget showing a quad."""

    widget_type_name = 'Quad'
    animation_properties = ('points', 'color', 'opacity', 'rotation', 'scale')

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str] = None, **kwargs) -> None:
        del kwargs
        super().__init__(mc=mc, config=config, key=key)

        # The points in this widget are always relative to the bottom left corner
        self.anchor_pos = ("left", "bottom")

        # Bind to all properties that when changed need to force
        # the widget to be redrawn
        self.bind(color=self._draw_widget,
                  points=self._draw_widget,
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
            KivyQuad(points=self.points)

    #
    # Properties
    #

    points = ListProperty([0, 0, 0, 100, 100, 100, 100, 0])
    '''The list of points to use to draw the widget in (x1, y1, x2, y2,
    x3, y3, x4, y4) format.

    :attr:`points` is a :class:`~kivy.properties.ListProperty`.
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


widget_classes = [Quad]
