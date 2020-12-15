"""Widget showing a rectangle."""
from typing import Optional
from kivy.graphics import Rectangle as KivyRectangle, RoundedRectangle
from kivy.graphics.context_instructions import Color, Rotate, Scale
from kivy.properties import NumericProperty

from mpfmc.uix.widget import Widget

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc     # pylint: disable-msg=cyclic-import,unused-import


class Rectangle(Widget):

    """Widget showing a rectangle."""

    widget_type_name = 'Rectangle'
    animation_properties = ('x', 'y', 'width', 'height', 'color', 'opacity', 'corner_radius',
                            'rotation', 'scale')

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str] = None, **kwargs) -> None:
        del kwargs
        super().__init__(mc=mc, config=config, key=key)

        # Bind to all properties that when changed need to force
        # the widget to be redrawn
        self.bind(pos=self._draw_widget,
                  size=self._draw_widget,
                  color=self._draw_widget,
                  rotation=self._draw_widget,
                  scale=self._draw_widget,
                  corner_radius=self._draw_widget,
                  corner_segments=self._draw_widget)

        self._draw_widget()

    def _draw_widget(self, *args) -> None:
        """Establish the drawing instructions for the widget."""
        del args

        if self.canvas is None:
            return

        anchor = (self.x - self.anchor_offset_pos[0], self.y - self.anchor_offset_pos[1])
        self.canvas.clear()

        with self.canvas:
            Color(*self.color)
            Rotate(angle=self.rotation, origin=anchor)
            Scale(self.scale).origin = anchor

            if self.corner_radius > 0:
                RoundedRectangle(pos=self.pos, size=self.size,
                                 radius=(self.corner_radius,
                                         self.corner_radius),
                                 segments=self.corner_segments)
            else:
                KivyRectangle(pos=self.pos, size=self.size)

    #
    # Properties
    #

    corner_radius = NumericProperty(0)
    '''Specifies the radius of the round corners of the rectangle.
     Defaults to 0.
    '''

    corner_segments = NumericProperty(10)
    '''Defines how many segments will be used for drawing the round
    corners. The drawing will be smoother if you have many segments.
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


widget_classes = [Rectangle]
