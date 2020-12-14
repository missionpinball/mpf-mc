from typing import List

from kivy.properties import NumericProperty, ListProperty, BooleanProperty

from mpfmc.uix.effects import EffectsChain
from mpfmc.effects.dot_filter import DotFilterEffect
from mpfmc.effects.gain import GainEffect
from mpfmc.effects.reduce import ReduceEffect

MYPY = False
if MYPY:   # pragma: no cover
    from kivy.uix.effectwidget import EffectBase    # pylint: disable-msg=cyclic-import,unused-import


class ColorDmdEffect(EffectsChain):
    """GLSL effect to render an on-screen DMD to look like individual round pixels."""

    dot_filter = BooleanProperty(True)
    '''
    Sets whether or not to apply the dot filter effect.

    dot_filter is a :class:`~kivy.properties.BooleanProperty` and
    defaults to True.
    '''

    width = NumericProperty(128)
    '''
    Sets the width in pixels of the display widget on the screen. Typically
    this is larger than the dots_x parameter.

    width is a :class:`~kivy.properties.NumericProperty` and
    defaults to 128.
    '''

    height = NumericProperty(32)
    '''
    Sets the height in pixels of the display widget on the screen. Typically
    this is larger than the dots_y parameter.

    height is a :class:`~kivy.properties.NumericProperty` and
    defaults to 32.
    '''

    dots_x = NumericProperty(128)
    '''
    Sets the number of dots in the horizontal (x) direction.

    dots_x is a :class:`~kivy.properties.NumericProperty` and
    defaults to 128.
    '''

    dots_y = NumericProperty(32)
    '''
    Sets the number of dots in the vertical (y) direction.

    dots_y is a :class:`~kivy.properties.NumericProperty` and
    defaults to 32.
    '''

    blur = NumericProperty(0.1)
    '''
    Sets the size of the blur around each pixel where it's blended with
    the background. The value is relative to the pixel. (e.g. a value of
    0.1 will add a 10% blur around the edge of each pixel.)

    blur is a :class:`~kivy.properties.NumericProperty` and
    defaults to 0.1.
    '''

    dot_size = NumericProperty(0.5)
    '''
    Sets the size of the circle for the dot/pixel relative to the size of the
    square bounding box of the dot. A size of 1.0 means that the diameter
    of the dot will be the same as its bounding box, in other words a
    size of 1.0 means that the dot will touch each other.

    dot_size is a :class:`~kivy.properties.NumericProperty` and
    defaults to 0.5.
    '''

    background_color = ListProperty([0.1, 0.1, 0.1, 1.0])
    '''
    A four-item tuple or list that represents the color of the space between the
    dots, in RGBA format with individual values as floats between 0.0 - 1.0. If
    you want the background to be transparent, set it to (0.0, 0.0, 0.0, 0.0).

    background_color is a :class:`~kivy.properties.ListProperty` and
    defaults to (0.1, 0.1, 0.1, 1.0) (which is 10% gray with 100% alpha/fully
    opaque).
    '''

    gain = NumericProperty(1.0)
    '''
    Sets the gain factor which is multiplied by each color channel.

    gain is a :class:`~kivy.properties.NumericProperty` and
    defaults to 1.0 (which has no effect).
    '''

    shades = NumericProperty(16)
    '''
    Sets the number of shades per channel to reduce it to.

    shades is a :class:`~kivy.properties.NumericProperty` and
    defaults to 16.
    '''

    def get_effects(self) -> List["EffectBase"]:
        effects = []

        if bool(self.dot_filter):
            effects.append(DotFilterEffect(
                width=self.width,
                height=self.height,
                dots_x=self.dots_x,
                dots_y=self.dots_y,
                blur=self.blur,
                dot_size=self.dot_size,
                background_color=self.background_color
            ))

        if self.shades > 0:
            effects.append(ReduceEffect(shades=self.shades))

        effects.append(GainEffect(gain=self.gain))

        return effects


effect_cls = ColorDmdEffect
name = 'color_dmd'
