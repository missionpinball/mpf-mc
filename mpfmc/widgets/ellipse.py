"""An ellipse widget."""
from typing import Optional
from kivy.graphics.vertex_instructions import Ellipse as KivyEllipse
from kivy.graphics.context_instructions import Color, Rotate, Scale
from kivy.properties import NumericProperty

from mpfmc.uix.widget import Widget

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc     # pylint: disable-msg=cyclic-import,unused-import


class Ellipse(Widget):

    """An ellipse widget."""

    widget_type_name = 'Ellipse'
    animation_properties = ('x', 'y', 'width', 'pos', 'height', 'size', 'color',
                            'angle_start', 'angle_end', 'opacity', 'rotation', 'scale')
    merge_settings = ('width', 'height')

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
                  segments=self._draw_widget,
                  angle_start=self._draw_widget,
                  angle_end=self._draw_widget)

        self._draw_widget()

    def _draw_widget(self, *args) -> None:
        del args

        if self.canvas is None:
            return

        anchor = (self.x - self.anchor_offset_pos[0], self.y - self.anchor_offset_pos[1])
        self.canvas.clear()

        with self.canvas:
            Color(*self.color)
            Rotate(angle=self.rotation, origin=anchor)
            Scale(self.scale).origin = anchor
            KivyEllipse(pos=self.pos, size=self.size,
                        segments=self.segments,
                        angle_start=self.angle_start,
                        angle_end=self.angle_end)

    #
    # Properties
    #

    segments = NumericProperty(180)
    '''Defines how many segments will be used for drawing the ellipse. The
    drawing will be smoother if you have many segments.
    '''

    angle_start = NumericProperty(0)
    '''Specifies the starting angle, in degrees, of the disk portion of
    the ellipse.
    '''

    angle_end = NumericProperty(360)
    '''Specifies the ending angle, in degrees, of the disk portion of
    the ellipse.
    '''

    rotation = NumericProperty(0)
    scale = NumericProperty(1.0)


widget_classes = [Ellipse]
