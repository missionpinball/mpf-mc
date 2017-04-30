from kivy.uix.effectwidget import EffectBase


class FlipVerticalEffect(EffectBase):
    """GLSL effect to vertically flip a texture"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.do_glsl()

    def do_glsl(self):
        self.glsl = flip_vertical_glsl


flip_vertical_glsl = '''
vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
{{
    return texture2D(texture, vec2(tex_coords.x, 1.0 - tex_coords.y));
}}
'''

effect_cls = FlipVerticalEffect
name = 'flip_vertical'
