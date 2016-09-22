from kivy.uix.effectwidget import EffectWidget, EffectBase
from kivy.uix.scatter import Scatter
from kivy.uix.widget import Widget, WidgetException

from mpfmc.core.utils import set_position
from mpfmc.uix.widget import MpfWidget
from kivy.uix.stencilview import StencilView


class Dmd(MpfWidget, Widget):
    widget_type_name = 'DMD'

    def __init__(self, mc, config, key=None, **kwargs):
        super().__init__(mc=mc, config=config, key=key)

        self.source = self.mc.displays[self.config['source_display']]

        self.dmd_frame = EffectWidget()

        if self.config['dot_filter']:
            self.dmd_frame.effects = [
                DmdLook(width=self.width,
                        height=self.height,
                        dmd_width=self.source.width,
                        blur=self.config['blur'],
                        pixel_size=self.config['pixel_size'],
                        bg_color=self.config['bg_color'])]

        self.add_widget(self.dmd_frame)

        self.dmd_frame.add_widget(DmdSource(mc, config, key))

        self.dmd_frame.size = self.size

    def __repr__(self):  # pragma: no cover
        try:
            return '<DMD size={}, source_size={}>'.format(
                    self.size, self.source.size)
        except AttributeError:
            return '<DMD size={}, source_size=(none)>'.format(
                    self.size)

    def on_pos(self, *args):
        self.dmd_frame.pos = set_position(self.parent.width,
                                  self.parent.height,
                                  self.width, self.height,
                                  self.config['x'],
                                  self.config['y'],
                                  self.config['anchor_x'],
                                  self.config['anchor_y'],
                                  self.config['adjust_top'],
                                  self.config['adjust_right'],
                                  self.config['adjust_bottom'],
                                  self.config['adjust_left'])


class ColorDmd(Dmd):
    widget_type_name = 'Color DMD'

    def __repr__(self):  # pragma: no cover
        try:
            return '<Color DMD size={}, source_size={}>'.format(
                    self.size, self.source.size)
        except AttributeError:
            return '<Color DMD size={}, source_size=(none)>'.format(
                    self.size)


class DmdSource(MpfWidget, Scatter, Widget):
    widget_type_name = 'DMD Source'

    def __init__(self, mc, config, key=None, **kwargs):
        super().__init__(mc=mc, config=config, key=key)

        self.source = self.mc.displays[self.config['source_display']]

        stencil = StencilView(size_hint=(None, None),
                              size=(self.source.config['width'],
                                    self.source.config['height']))

        # Add the effects to make this look like a DMD
        effect_list = list()

        if 'luminosity' in self.config:
            effect_list.append(Monochrome(r=self.config['luminosity'][0],
                                          g=self.config['luminosity'][1],
                                          b=self.config['luminosity'][2]))

        if self.config['shades']:
            effect_list.append(Reduce(shades=self.config['shades']))

        if self.config['pixel_color']:
            effect_list.append(Colorize(r=self.config['pixel_color'][0],
                                        g=self.config['pixel_color'][1],
                                        b=self.config['pixel_color'][2]))

        if self.config['gain'] != 1.0:
            effect_list.append(Gain(gain=self.config['gain']))

        effect = EffectWidget()
        effect.effects = effect_list

        stencil.add_widget(effect)

        self.add_widget(stencil)

        try:
            effect.add_widget(self.source)
        except WidgetException:
            self.source.parent = None
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

    """GLSL effect to render an on-screen DMD to look like individual round pixels.

    Args:
        width: The width in pixels of the DMD widget on the screen. Typically
            this is larger than the dmd_width.
        height: The height in pixels of the DMD widget on the screen.
        dmd_width: The width in pixels of the original DMD that you're
            emulating. (e.g. 128)
        dmd_height: The height in pixels of the original DMD that you're
            emulating. (e.g. 32)
        blur: A floating point value that represents the size of the blue
            around each pixel where it's blended with the background. The value
            is relative to the pixel. (e.g. a value of 0.1 will add a 10% blur
            around the edge of each pixel.) Default is 0.1.
        pixel_size: The size of the circle for the pixel relative to the size
            of the square bounding box of the pixel. A size of 1.0 means that
            the diameter of the pixel will be the same as its bounding box, in
            other words a size of 1.0 means that the pixels will touch each
            other. Default is 0.5.
        bg_color: A four-item tuple or list that represents the color of the
            space between the pixels, in RGBA format with individual values as
            floats between 0.0 - 1.0. the default is (0.1, 0.1, 0.1, 1.0) which
            is 10% gray with 100% alpha (fully opaque). If you want the
            background to be transparent, set it to (0.0, 0.0, 0.0, 0.0)


    This shader is based on code from a tutorial by Jason Gorski.
    http://www.lighthouse3d.com/opengl/ledshader/

    Potential bug: This GLSL filter seems to not work on Windows 10 running on
    VMware Fusion on Mac OS X. It works fine on Windows 10 native as well as
    Mac OS X Native.
    """

    # pylint: disable-msg=too-many-arguments
    def __init__(self, width, height, dmd_width, blur=0.1,
                 pixel_size=0.6, bg_color=(0.1, 0.1, 0.1, 1.0)):
        """Initialise DMD Look."""
        super().__init__()

        blur = float(blur)
        pixel_radius = pixel_size / 2.0
        new_pixel_size = width / dmd_width
        width = float(width)
        height = float(height)
        bg_color = tuple(map(float, bg_color))

        self.glsl = '''

        float blur = {};
        float pixelRadius = {};
        float pixelSize = {};

        vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
        {{
            vec2 texCoordsStep = 1.0/(vec2({},{})/pixelSize);
            vec2 pixelRegionCoords = fract(tex_coords.xy/texCoordsStep);

            vec2 powers = pow(abs(pixelRegionCoords - 0.5),vec2(2.0));
            float radiusSqrd = pow(pixelRadius,2.0);
            float gradient = smoothstep(radiusSqrd-blur, radiusSqrd+blur, powers.x+powers.y);

            vec4 newColor = mix(color, vec4({}, {}, {}, {}), gradient);
            return newColor;
        }}

        '''.format(blur, pixel_radius, new_pixel_size, width, height,
                   *bg_color)
