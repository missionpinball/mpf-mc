from kivy.uix.effectwidget import EffectWidget, EffectBase
from kivy.uix.scatter import Scatter
from kivy.uix.widget import Widget

from mc.core.utils import set_position
from mc.uix.widget import MpfWidget
from kivy.uix.stencilview import StencilView


class Dmd(MpfWidget, Widget):
    widget_type_name = 'DMD'

    def __init__(self, mc, config, slide, mode=None, priority=None, **kwargs):
        super().__init__(mc=mc, mode=mode, priority=priority, slide=slide,
                         config=config)

        self.source = self.mc.displays[self.config['source_display']]

        self.dmd_frame = EffectWidget()
        self.dmd_frame.effects = [DmdLook(128, 32)]
        self.add_widget(self.dmd_frame)

        self.dmd_frame.add_widget(DmdSource(mc, config, slide, mode, priority))

        self.dmd_frame.size = self.size

        self.dmd_frame.pos = set_position(slide.width,
                                          slide.height,
                                          self.width, self.height,
                                          self.config['x'],
                                          self.config['y'],
                                          self.config['anchor_x'],
                                          self.config['anchor_y'])


class DmdSource(MpfWidget, Scatter, Widget):
    widget_type_name = 'DMD Source'

    def __init__(self, mc, config, slide, mode=None, priority=None, **kwargs):

        super().__init__(mc=mc, mode=mode, priority=priority, slide=slide,
                         config=config)

        self.source = self.mc.displays[self.config['source_display']]

        stencil = StencilView(size_hint=(None, None),
                              size=(self.source.config['width'],
                                    self.source.config['height']))

        # Add the effects to make this look like a DMD
        effect_list = list()
        effect_list.append(Monochrome(r=self.config['luminosity'][0],
                                      g=self.config['luminosity'][1],
                                      b=self.config['luminosity'][2]))

        if self.config['shades']:
            effect_list.append(Reduce(shades=self.config['shades']))

        effect_list.append(Colorize(r=self.config['color'][0],
                                    g=self.config['color'][1],
                                    b=self.config['color'][2]))

        if self.config['gain'] != 1.0:
            effect_list.append(Gain(gain=self.config['gain']))

        effect = EffectWidget()
        effect.effects = effect_list

        stencil.add_widget(effect)

        self.add_widget(stencil)

        effect.add_widget(self.source)
        effect.size = (self.config['width'], self.config['height'])

        effect.texture.mag_filter = 'nearest'
        effect.texture.min_filter = 'nearest'

        self.scale = min(self.width / self.source.width,
                         self.height / self.source.height)

        self.pos = (0, 0)


class Monochrome(EffectBase):
    """GLSL effect to convert the texture to monochrome.

    Args:
        r: The luminance factor for the red component. Default is 0.299.
        g: The luminance factor for the green component. Default is 0.587.
        b: The luminance factor for the blue component. Default is 0.114.

    Note that r, g, b, input values expect a float from 0.0 to 1.0.

    More information here:
    http://www.johndcook.com/blog/2009/08/24/algorithms-convert-color-grayscale/

    """

    def __init__(self, r=.299, g=.587, b=.114):
        super().__init__()

        r = float(r)
        g = float(g)
        b = float(b)

        self.glsl = '''

        vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
        {{
            float lum = ((color.x * {}) + (color.y * {}) + (color.z * {}));
            return vec4(lum, lum, lum, 1.0);
        }}
        '''.format(r, g, b)


class Reduce(EffectBase):
    """GLSL effect to reduce a texture to fewer bits per color channel.

    Args:
        shades: The number of shades per channel to reduce it to. Default is
            16.

    """

    def __init__(self, shades=16):
        super().__init__()

        shades = abs(float(shades - 1))

        self.glsl = '''

        vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)

        {{
        float bitDepth = {};
        vec4 outColor = vec4(floor(color.x * bitDepth) / bitDepth,
                             floor(color.y * bitDepth) / bitDepth,
                             floor(color.z * bitDepth) / bitDepth,
                             1.0);
        return outColor;
        }}

                '''.format(shades)


class Colorize(EffectBase):
    """GLSL effect to apply a color tint to a texture.

    Args:
        r: The color factor for the red component. Default is 1.0.
        g: The color factor for the green component. Default is 0.4.
        b: The color factor for the blue component. Default is 0.0.

    Note that r, g, b, input values expect a float from 0.0 to 1.0.

    """

    def __init__(self, r=1.0, g=.4, b=0.0):
        super().__init__()

        r = float(r)
        g = float(g)
        b = float(b)

        self.glsl = '''

        vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
        {{
            vec4 c = vec4(color.x * {}, color.y * {}, color.z * {}, 1.0);
            return c;
        }}
        '''.format(r, g, b)


class Gain(EffectBase):
    """GLSL effect to apply apply a gain (brightness) adjustment to a texture.

    Args:
        gain: Float which adjusts the values. Default is 1.0 which has no
            effect, higher or lower values are multiplied by each color
            channel.

    """

    def __init__(self, gain=1.0):
        super().__init__()

        gain = float(gain)

        self.glsl = '''

        vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)

        {{
        vec4 outColor = vec4(color.x * {0}, color.y * {0}, color.z * {0}, 1.0);
        return outColor;
        }}
        '''.format(gain)


class DmdLook(EffectBase):
    """This method currently does nothing and needs to be written by someone
    who knows C and/or GLSL.

    This effect is passed the texture after it's been scaled up for the on-
    screen window. It's also passed w and h parameters which are the original
    width and height of the DMD.

    For example, for a standard 128x32 DMD which is displayed on the screen at
    640x160, w will be 128 and h will be 32. The pixel indices will be from
    (0,0) -> (639,159).

    So we need to figure out how to look at a pixel and decide what color to
    set it based on whether it's in the center of a pixel or whether it's in
    a gap between pixels.

    Eventually we can have settings for pixel size and aliasing and stuff, but
    for now if we can just make some pixels black that would be good.

    Details about how the code here plugs into Kivy:
    https://kivy.org/docs/api-kivy.uix.effectwidget.html#creating-effects

    For now if anyone can figure out how to write the GLSL code, you can just
    hard-code with a DMD size of 128x32 and an on screen size of 640x160. I'll
    convert it to be dynamic later.

    There's a simple test you can run to see the results:
    python -m unittest tests.test_Dmd

    Or if you are using the Kivy Python:
    kivy -m unittest tests.test_Dmd

    You can confirm that this GLSL code is being called by, for example,
    changing the "color.z" to "1.0" below and seeing that the DMD on screen has
    it's blue channel set to 100%.

    BTW, there's another GLSL option where we could create a texture with
    circular dots that are white on alpha transparent background and then do a
    pixel-by-pixel blending, but I don't know how to do that. (In that case we
    can dynamically generate the mask texture based on the original and on-
    screen size of the DMD.) But I don't know how to write a function in GLSL
    that would receive this. We might have to use a different base class other
    than EffectBase. There's an example of that here:

    https://github.com/kivy/kivy/blob/master/examples/canvas/multitexture.py

    """

    def __init__(self, w=128, h=32):
        super().__init__()

        self.glsl = '''

        float tolerance = 0.0;
        float pixelRadius = .3;
        int pixelSize = 5;

        vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
        {
            vec2 texCoordsStep = 1.0/(vec2(float(600),float(160))/float(pixelSize));
            vec2 pixelRegionCoords = fract(tex_coords.xy/texCoordsStep);

            vec2 powers = pow(abs(pixelRegionCoords - 0.5),vec2(2.0));
            float radiusSqrd = pow(pixelRadius,2.0);
            float gradient = smoothstep(radiusSqrd-tolerance, radiusSqrd+tolerance, powers.x+powers.y);

            vec4 newColor = mix(color, vec4(0.1, 0.1, 0.1, 1.0), gradient);
            return newColor;
        }

        '''
