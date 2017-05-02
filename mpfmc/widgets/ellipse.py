from kivy.graphics.vertex_instructions import Ellipse as KivyEllipse
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ListProperty

from mpfmc.uix.widget import MpfWidget


class Ellipse(MpfWidget, Widget):

    widget_type_name = 'Ellipse'

    def on_pos(self, *args):
        del args

        # TODO: refactor positioning to allow animation (don't use config settings)
        self.pos = self.calculate_position(self.parent.width,
                                           self.parent.height,
                                           self.width, self.height,
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
            KivyEllipse(pos=self.pos, size=self.size,
                        segments=self.segments,
                        angle_start=self.angle_start,
                        angle_end=self.angle_end)

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

widget_classes = [Ellipse]
