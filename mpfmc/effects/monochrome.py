from kivy.uix.effectwidget import EffectBase
from kivy.properties import ListProperty


class MonochromeEffect(EffectBase):
    """GLSL effect to convert the texture to monochrome.

    More information here:
    http://www.johndcook.com/blog/2009/08/24/algorithms-convert-color-grayscale/

    """

    luminosity = ListProperty([.299, .587, .114])
    '''This defines the luminosity factor for each color channel. The value
    for each channel must be between 0.0 and 1.0.

    :attr:`luminosity` is a :class:`ListProperty` defaults to
    (.299, .587, .114)
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.do_glsl()

    def on_luminosity(self, *args):
        self.do_glsl()

    def do_glsl(self):
        self.glsl = monochrome_glsl.format(float(self.luminosity[0]),
                                           float(self.luminosity[1]),
                                           float(self.luminosity[2]))


monochrome_glsl = '''
vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
{{
    float lum = ((color.x * {}) + (color.y * {}) + (color.z * {}));
    return vec4(lum, lum, lum, 1.0);
}}
'''

effect_cls = MonochromeEffect
name = 'monochrome'
