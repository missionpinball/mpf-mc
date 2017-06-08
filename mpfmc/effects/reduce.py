from kivy.uix.effectwidget import EffectBase
from kivy.properties import NumericProperty


class ReduceEffect(EffectBase):
    """GLSL effect to reduce a texture to fewer bits per color channel."""

    shades = NumericProperty(16)
    '''
    Sets the number of shades per channel to reduce it to.

    shades is a :class:`~kivy.properties.NumericProperty` and
    defaults to 16.
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.do_glsl()

    def on_shades(self, *args):
        self.do_glsl()

    def do_glsl(self):
        self.glsl = reduce_glsl.format(abs(float(self.shades - 1)))


reduce_glsl = '''
        vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
        {{
        float bitDepth = {};
        vec4 outColor = vec4(floor(color.x * bitDepth) / bitDepth,
                             floor(color.y * bitDepth) / bitDepth,
                             floor(color.z * bitDepth) / bitDepth,
                             1.0);
        return outColor;
        }}
        '''


effect_cls = ReduceEffect
name = 'reduce'
