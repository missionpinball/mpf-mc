from typing import TYPE_CHECKING, Optional
from kivy.graphics.vertex_instructions import Ellipse as KivyEllipse
from kivy.graphics.context_instructions import Color, Rotate, Scale, PushMatrix, PopMatrix
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ListProperty

from mpfmc.uix.widget import MpfWidget

if TYPE_CHECKING:
    from mpfmc.core.mc import MpfMc


class Ellipse(MpfWidget, Widget):

    widget_type_name = 'Ellipse'
    animation_properties = ('x', 'y', 'width', 'pos', 'height', 'size', 'color',
                            'angle_start', 'angle_end', 'opacity', 'rotation', 'scale')
    merge_settings = ('width', 'height')

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str]=None, **kwargs) -> None:
        del kwargs
        super().__init__(mc=mc, config=config, key=key)

        self.rotation = config.get('rotation', 0)
        self.scale = config.get('scale', 1.0)
        self._draw_widget()

    def _draw_widget(self) -> None:
        self.canvas.clear()
        with self.canvas.before:
            PushMatrix()
        with self.canvas:
            Color(*self.color)
            Scale(self.scale, origin=self.center)
            Rotate(angle=self.rotation, origin=self.center)
            KivyEllipse(pos=self.pos, size=self.size,
                        segments=self.segments,
                        angle_start=self.angle_start,
                        angle_end=self.angle_end)
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

    def on_angle_start(self, *args):
        del args
        self._draw_widget()

    def on_angle_end(self, *args):
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
