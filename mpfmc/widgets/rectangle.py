from kivy.graphics import Rectangle as KivyRectangle
from kivy.graphics import RoundedRectangle
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ListProperty

from mpfmc.uix.widget import MpfWidget


class Rectangle(MpfWidget, Widget):

    widget_type_name = 'Rectangle'
    animation_properties = ('x', 'y', 'color', 'opacity', 'corner_radius')

    def on_pos(self, *args) -> None:
        del args

        # TODO: refactor positioning to allow animation (don't use config settings)
        self.pos = self.calculate_position(self.parent.width,
                                           self.parent.height,
                                           self.width,
                                           self.height,
                                           self.config['x'],
                                           self.config['y'],
                                           self.config['anchor_x'],
                                           self.config['anchor_y'],
                                           self.config['adjust_top'],
                                           self.config['adjust_right'],
                                           self.config['adjust_bottom'],
                                           self.config['adjust_left'])

        with self.canvas:
            Color(*self.color)

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

widget_classes = [Rectangle]
