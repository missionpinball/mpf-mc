from kivy.uix.effectwidget import EffectBase
from kivy.properties import NumericProperty


class GammaEffect(EffectBase):
    """GLSL effect to apply a gamma setting to a texture"""

    gamma = NumericProperty(1.0)
    '''
    Sets the gamma factor.

    gamma is a :class:`~kivy.properties.NumericProperty` and
    defaults to 1.0 (which has no effect).
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.do_glsl()

    def on_gamma(self, *args):
        self.do_glsl()

    def do_glsl(self):
        self.glsl = gamma_glsl.format(float(self.gamma))


gamma_glsl = '''
vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
{{
    vec4 outColor = vec4(pow(color.x, {0}), pow(color.y, {0}), pow(color.z, {0}), 1.0);
    return outColor;
}}
'''

effect_cls = GammaEffect
name = 'gamma'
