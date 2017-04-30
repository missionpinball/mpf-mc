from kivy.properties import ListProperty
from kivy.uix.effectwidget import EffectBase


class ColorizeEffect(EffectBase):
    """GLSL effect to apply a color tint to a texture."""

    tint_color = ListProperty([1, 0.4, 0, 0])
    '''This defines the color of the tint to be used in the effect.

    :attr:`tint_color` is a :class:`ListProperty` defaults to
    (1, 0.4, 1, 0)
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.do_glsl()

    def on_tint_color(self, *args):
        self.do_glsl()

    def do_glsl(self):
        self.glsl = colorize_glsl.format(float(self.tint_color[0]),
                                         float(self.tint_color[1]),
                                         float(self.tint_color[2]))


colorize_glsl = '''
        vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
        {{
            vec4 c = vec4(color.x * {}, color.y * {}, color.z * {}, 1.0);
            return c;
        }}
        '''

effect_cls = ColorizeEffect
name = 'colorize'
