from kivy.properties import NumericProperty
from kivy.uix.effectwidget import EffectBase


class GlowEffect(EffectBase):

    """GLSL effect to apply a glowing effect to a texture."""

    blur_size = NumericProperty(4.0)
    intensity = NumericProperty(.5)
    glow_amplitude = NumericProperty(0.1)
    glow_speed = NumericProperty(1.0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.do_glsl()

    def on_blur_size(self, *args):
        self.do_glsl()

    def on_intensity(self, *args):
        self.do_glsl()

    def on_glow_speed(self, *args):
        self.do_glsl()

    def on_glow_amplitude(self, *args):
        self.do_glsl()

    def do_glsl(self):
        self.glsl = glow_glsl.format(float(self.blur_size),
                                     float(self.intensity),
                                     float(self.glow_amplitude),
                                     float(self.glow_speed))


glow_glsl = '''
vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
{{
    float blurSize = {0}/resolution.x;
    vec4 sum = vec4(0.0);
    sum += texture(texture, vec2(tex_coords.x - 4.0 * blurSize, tex_coords.y)) * .05;
    sum += texture(texture, vec2(tex_coords.x - 3.0*blurSize, tex_coords.y)) * 0.09;
    sum += texture(texture, vec2(tex_coords.x - 2.0*blurSize, tex_coords.y)) * 0.12;
    sum += texture(texture, vec2(tex_coords.x - blurSize, tex_coords.y)) * 0.15;
    sum += texture(texture, vec2(tex_coords.x, tex_coords.y)) * 0.16;
    sum += texture(texture, vec2(tex_coords.x + blurSize, tex_coords.y)) * 0.15;
    sum += texture(texture, vec2(tex_coords.x + 2.0*blurSize, tex_coords.y)) * 0.12;
    sum += texture(texture, vec2(tex_coords.x + 3.0*blurSize, tex_coords.y)) * 0.09;
    sum += texture(texture, vec2(tex_coords.x + 4.0*blurSize, tex_coords.y)) * 0.05;
    sum += texture(texture, vec2(tex_coords.x, tex_coords.y - 4.0*blurSize)) * 0.05;
    sum += texture(texture, vec2(tex_coords.x, tex_coords.y - 3.0*blurSize)) * 0.09;
    sum += texture(texture, vec2(tex_coords.x, tex_coords.y - 2.0*blurSize)) * 0.12;
    sum += texture(texture, vec2(tex_coords.x, tex_coords.y - blurSize)) * 0.15;
    sum += texture(texture, vec2(tex_coords.x, tex_coords.y)) * 0.16;
    sum += texture(texture, vec2(tex_coords.x, tex_coords.y + blurSize)) * 0.15;
    sum += texture(texture, vec2(tex_coords.x, tex_coords.y + 2.0*blurSize)) * 0.12;
    sum += texture(texture, vec2(tex_coords.x, tex_coords.y + 3.0*blurSize)) * 0.09;
    sum += texture(texture, vec2(tex_coords.x, tex_coords.y + 4.0*blurSize)) * 0.05;
    vec4 result = texture(texture, tex_coords);
    result = sum * ({2}*sin(2*3.14*{3}*time) + {1})  + result;
    return result;
}}
'''

effect_cls = GlowEffect
name = 'glow'
