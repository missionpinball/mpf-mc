from typing import Optional
from kivy.graphics import Line as KivyLine
from kivy.graphics.context_instructions import Color
from kivy.properties import (ListProperty, NumericProperty, OptionProperty,
                             BooleanProperty)
from kivy.uix.widget import Widget
from mpfmc.uix.widget import MpfWidget
from mpfmc.core.mc import MpfMc


class Bezier(MpfWidget, Widget):

    widget_type_name = 'Bezier'

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str]=None, **kwargs) -> None:
        del kwargs
        super().__init__(mc=mc, config=config, key=key)

        with self.canvas:
            Color(*self.color)
            KivyLine(bezier=self.points,
                     width=self.thickness,
                     cap=self.cap,
                     joint=self.joint,
                     cap_precision=self.cap_precision,
                     joint_precision=self.joint_precision,
                     close=self.close,
                     bezier_precision=self.precision)

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

    precision = NumericProperty(180)
    '''Number of iteration for drawing the bezier between 2 segments, defaults to 
    180. The precision must be at least 1.
    '''

    thickness = NumericProperty(1.0)
    '''Width of the bezier line.

    :attr:`thickness` is a :class:`~kivy.properties.NumericProperty` and defaults
    to 1.0.
    '''

widget_classes = [Bezier]
