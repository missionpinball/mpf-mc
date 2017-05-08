from kivy.graphics import Line as KivyLine
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget
from kivy.properties import (ListProperty, NumericProperty, OptionProperty,
                             BooleanProperty)

from mpfmc.uix.widget import MpfWidget


class Line(MpfWidget, Widget):

    widget_type_name = 'Line'
    animation_properties = ('x', 'y', 'points', 'thickness', 'color', 'opacity')

    def on_pos(self, *args) -> None:
        del args

    def _draw_widget(self):
        self.canvas.clear()
        with self.canvas:
            Color(*self.color)
            KivyLine(points=self.points,
                     width=self.thickness,
                     cap=self.cap,
                     joint=self.joint,
                     cap_precision=self.cap_precision,
                     joint_precision=self.joint_precision,
                     close=self.close)

    def on_parent(self, instance, parent):
        del instance
        self.pos = self.calculate_position(parent.width,
                                           parent.height,
                                           self.width, self.height,
                                           self.config['x'],
                                           self.config['y'],
                                           self.config['anchor_x'],
                                           self.config['anchor_y'],
                                           self.config['adjust_top'],
                                           self.config['adjust_right'],
                                           self.config['adjust_bottom'],
                                           self.config['adjust_left'])
        self._draw_widget()

    def on_points(self, *args):
        del args
        self._draw_widget()

    def on_thickness(self, *args):
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

    points = ListProperty()
    '''The list of points to use to draw the widget in (x1, y1, x2, y2...)
    format.

    :attr:`points` is a :class:`~kivy.properties.ListProperty`.
    '''

    cap = OptionProperty("round", options=["none", "square", "round"])
    '''The cap of the line, defaults to 'round'. Can be one of 'none',
    'square' or 'round'
    '''

    cap_precision = NumericProperty(10)
    '''Number of iterations for drawing the "round" cap, defaults to 10. The
    cap_precision must be at least 1.
    '''

    close = BooleanProperty(False)
    '''If True, the line will be closed.
    '''

    joint = OptionProperty("round", options=["none", "round", "bevel", "miter"])
    '''The join of the line, defaults to 'round'. Can be one of 'none', 'round', 
    'bevel', 'miter'.
    '''

    joint_precision = NumericProperty(10)
    '''Number of iterations for drawing the "round" joint, defaults to 10. The
    joint_precision must be at least 1.
    '''

    thickness = NumericProperty(1.0)
    '''Width of the line.

    :attr:`thickness` is a :class:`~kivy.properties.NumericProperty` and defaults
    to 1.0.
    '''

widget_classes = [Line]
