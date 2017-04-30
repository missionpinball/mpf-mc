from kivy.uix.effectwidget import EffectBase
from kivy.properties import NumericProperty


class GainEffect(EffectBase):
    """GLSL effect to apply apply a gain (brightness) adjustment to a texture.

    Args:
        gain: Float which adjusts the values. Default is 1.0 which has no
            effect, higher or lower values are multiplied by each color
            channel.

    """
    gain = NumericProperty(1.0)
    '''
    Sets the gain factor which is multiplied by each color channel.

    gain is a :class:`~kivy.properties.NumericProperty` and
    defaults to 1.0 (which has no effect).
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.do_glsl()

    def on_gain(self, *args):
        self.do_glsl()

    def do_glsl(self):
        self.glsl = gain_glsl.format(float(self.gain))


gain_glsl = '''
vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
{{
vec4 outColor = vec4(color.x * {0}, color.y * {0}, color.z * {0}, 1.0);
return outColor;
}}
'''

effect_cls = GainEffect
name = 'gain'
