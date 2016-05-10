from kivy.graphics import Point as KivyPoint
from kivy.graphics.context_instructions import Color
from kivy.uix.widget import Widget
from mpfmc.uix.widget import MpfWidget


class Point(MpfWidget, Widget):

    widget_type_name = 'Line'

    def __init__(self, mc, config, slide, key=None, **kwargs):
        config['pointsize'] = config.pop('size')

        super().__init__(mc=mc, slide=slide, config=config, key=key)

        with self.canvas:
            Color(*self.config['color'])
            KivyPoint(points=self.config['points'],
                      pointsize=self.config['pointsize'])
