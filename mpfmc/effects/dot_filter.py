from kivy.uix.effectwidget import EffectBase
from kivy.properties import NumericProperty, ListProperty


class DotFilterEffect(EffectBase):

    """GLSL effect to render an on-screen dot filter to look like individual round
    dots/pixels (simulating a DMD).

    This shader is based on code from a tutorial by Jason Gorski.
    http://www.lighthouse3d.com/opengl/ledshader/

    Potential bug: This GLSL filter seems to not work on Windows 10 running on
    VMware Fusion on Mac OS X. It works fine on Windows 10 native as well as
    Mac OS X Native.
    """

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.do_glsl()

    def on_width(self, *args):
        self.do_glsl()

    def on_height(self, *args):
        self.do_glsl()

    def on_dots_x(self, *args):
        self.do_glsl()

    def on_dots_y(self, *args):
        self.do_glsl()

    def on_blur(self, *args):
        self.do_glsl()

    def on_dot_size(self, *args):
        self.do_glsl()

    def on_background_color(self, *args):
        self.do_glsl()

    def do_glsl(self):
        background_color = tuple(map(float, self.background_color))
        dot_size = min(self.width / self.dots_x, self.height / self.dots_y)

        self.glsl = dot_filter_glsl.format(float(self.blur),
                                           self.dot_size / 2.0,
                                           dot_size,
                                           float(self.width),
                                           float(self.height),
                                           *background_color)


dot_filter_glsl = '''
        float blur = {};
        float dotRadius = {};
        float dotSize = {};

        vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
        {{
            vec2 texCoordsStep = 1.0/(vec2({},{})/dotSize);
            vec2 dotRegionCoords = fract(tex_coords.xy/texCoordsStep);

            vec2 powers = pow(abs(dotRegionCoords - 0.5),vec2(2.0));
            float radiusSqrd = pow(dotRadius,2.0);
            float gradient = smoothstep(radiusSqrd-blur, radiusSqrd+blur, powers.x+powers.y);

            vec4 newColor = mix(color, vec4({}, {}, {}, {}), gradient);
            return newColor;
        }}
        '''

effect_cls = DotFilterEffect
name = 'dot_filter'
