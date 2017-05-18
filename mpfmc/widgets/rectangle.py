from typing import TYPE_CHECKING, Optional
from kivy.graphics import Rectangle as KivyRectangle, RoundedRectangle
from kivy.graphics.context_instructions import Color, Rotate, Scale, PushMatrix, PopMatrix
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ListProperty, ReferenceListProperty

from mpfmc.uix.widget_wrapper import WidgetWrapper

if TYPE_CHECKING:
    from mpfmc.core.mc import MpfMc


class Rectangle(WidgetWrapper):

    widget_type_name = 'Rectangle'
    animation_properties = ('x', 'y', 'width', 'height', 'color', 'opacity', 'corner_radius',
                            'rotation', 'scale')

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str]=None, **kwargs) -> None:
        del kwargs
        super().__init__(mc=mc, config=config, key=key)

    def _create_child_widget(self) -> "Widget":
        """Create the rectangle widget and set its initial property values."""
        rectangle = CoreRectangle(width=0, height=0, size_hint=(None, None))
        rectangle.color = self.config['color']
        rectangle.opacity = self.config['opacity']
        rectangle.rotation = self.config['rotation']
        rectangle.scale = self.config['scale']
        rectangle.width = self.config['width']
        rectangle.height = self.config['height']

        return rectangle

    def _bind_child_widget_properties(self, widget: "Widget"):
        widget.bind(size=self.on_widget_size)


class CoreRectangle(Widget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Bind to all properties that when changed need to force
        # the widget to be redrawn
        self.bind(pos=self._draw_widget,
                  size=self._draw_widget,
                  color=self._draw_widget,
                  rotation=self._draw_widget,
                  scale=self._draw_widget,
                  corner_radius=self._draw_widget,
                  corner_segments=self._draw_widget)

    def _draw_widget(self, *args) -> None:
        """Establish the drawing instructions for the widget."""
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

            if self.corner_radius > 0:
                RoundedRectangle(pos=self.pos, size=self.size,
                                 radius=(self.corner_radius,
                                         self.corner_radius),
                                 segments=self.corner_segments)
            else:
                KivyRectangle(pos=self.pos, size=self.size)

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

    anchor_offset_x = NumericProperty(0)
    anchor_offset_y = NumericProperty(0)
    anchor_offset = ReferenceListProperty(anchor_offset_x, anchor_offset_y)

widget_classes = [Rectangle]
