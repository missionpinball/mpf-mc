from typing import TYPE_CHECKING, Optional
from kivy.graphics import Rectangle as KivyRectangle
from kivy.graphics import RoundedRectangle
from kivy.graphics.context_instructions import Color, Rotate, Scale, PushMatrix, PopMatrix
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ListProperty

from mpfmc.uix.widget import MpfWidget

if TYPE_CHECKING:
    from mpfmc.core.mc import MpfMc


class Rectangle(MpfWidget, Widget):

    widget_type_name = 'Rectangle'
    animation_properties = ('x', 'y', 'width', 'height', 'color', 'opacity', 'corner_radius',
                            'rotation', 'scale')

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str]=None, **kwargs) -> None:
        del kwargs
        super().__init__(mc=mc, config=config, key=key)
        self._draw_widget()

    def _draw_widget(self) -> None:
        """Establish the drawing instructions for the widget."""
        self.canvas.clear()
        with self.canvas.before:
            PushMatrix()
        with self.canvas:
            Color(*self.color)
            Scale(self.scale, origin=self.center)
            Rotate(angle=self.rotation, origin=self.center)

            if self.corner_radius > 0:
                RoundedRectangle(pos=self.pos, size=self.size,
                                 radius=(self.corner_radius,
                                         self.corner_radius),
                                 segments=self.corner_segments)
            else:
                KivyRectangle(pos=self.pos, size=self.size)
        with self.canvas.after:
            PopMatrix()

    def on_pos(self, *args):
        del args
        self._draw_widget()

    def on_size(self, *args):
        del args
        self._draw_widget()

    def on_color(self, *args):
        del args
        self._draw_widget()

    def on_corner_radius(self, *args):
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
