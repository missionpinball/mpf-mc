from typing import TYPE_CHECKING, Optional
from kivy.graphics.vertex_instructions import Ellipse as KivyEllipse
from kivy.graphics.context_instructions import Color, PushMatrix, PopMatrix, Rotate, Scale
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ListProperty, ReferenceListProperty

from mpfmc.uix.widget_wrapper import WidgetWrapper

if TYPE_CHECKING:
    from mpfmc.core.mc import MpfMc


class Ellipse(WidgetWrapper):

    widget_type_name = 'Ellipse'
    animation_properties = ('x', 'y', 'width', 'pos', 'height', 'size', 'color',
                            'angle_start', 'angle_end', 'opacity', 'rotation', 'scale')
    merge_settings = ('width', 'height')

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str]=None, **kwargs) -> None:
        del kwargs
        super().__init__(mc=mc, config=config, key=key)

    def _create_child_widget(self) -> "Widget":
        """Create the ellipse widget and set its initial property values."""
        ellipse = CoreEllipse(width=0, height=0, size_hint=(None, None))
        ellipse.color = self.config['color']
        ellipse.segments = self.config['segments']
        ellipse.angle_start = self.config['angle_start']
        ellipse.angle_end = self.config['angle_end']
        ellipse.opacity = self.config['opacity']
        ellipse.rotation = self.config['rotation']
        ellipse.scale = self.config['scale']
        ellipse.width = self.config['width']
        ellipse.height = self.config['height']

        return ellipse

    def _bind_child_widget_properties(self, widget: "Widget"):
        widget.bind(size=self.on_widget_size)


class CoreEllipse(Widget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.bind(pos=self._draw_widget,
                  size=self._draw_widget,
                  color=self._draw_widget,
                  rotation=self._draw_widget,
                  scale=self._draw_widget,
                  segments=self._draw_widget,
                  angle_start=self._draw_widget,
                  angle_end=self._draw_widget)

    def _draw_widget(self, *args) -> None:
        del args

        if self.canvas is None:
            return

        anchor = (self.x - self.anchor_offset_x, self.y - self.anchor_offset_y)
        self.canvas.clear()

        with self.canvas.before:
            PushMatrix()

        with self.canvas:
            Color(*self.color)
            Rotate(angle=self.rotation, origin=anchor)
            Scale(self.scale).origin = anchor
            KivyEllipse(pos=self.pos, size=self.size,
                        segments=self.segments,
                        angle_start=self.angle_start,
                        angle_end=self.angle_end)

        with self.canvas.after:
            PopMatrix()

    def on_parent(self, instance, parent):
        del instance
        parent.bind(pos=self.update_anchor_offset)

    def update_anchor_offset(self, instance, pos):
        del instance
        self.anchor_offset = pos
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

    anchor_offset_x = NumericProperty(0)
    anchor_offset_y = NumericProperty(0)

    anchor_offset = ReferenceListProperty(anchor_offset_x, anchor_offset_y)


widget_classes = [Ellipse]
