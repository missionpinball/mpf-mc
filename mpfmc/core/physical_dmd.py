"""Physical DMD."""
import struct
from kivy.clock import Clock
from kivy.graphics.fbo import Fbo
from kivy.graphics.opengl import glReadPixels, GL_RGB, GL_UNSIGNED_BYTE
from kivy.graphics.texture import Texture
from kivy.uix.effectwidget import EffectWidget, EffectBase

from mpfmc.widgets.dmd import Gain


class PhysicalDmdBase(object):

    """Base class for DMD devices."""

    dmd_name_string = 'Physical DMD'

    def __init__(self, mc, name, config):
        """Initialise DMD."""

        self.mc = mc
        self.name = name

        self.mc.log.info('Initializing Physical DMD')

        self.config = self._get_validated_config(config)

        self.source = self.mc.displays[self.config['source_display']]
        self.prev_data = None

        # put the widget canvas on a Fbo
        texture = Texture.create(size=self.source.size, colorfmt='rgb')
        self.fbo = Fbo(size=self.source.size, texture=texture)

        self.effect_widget = EffectWidget()

        effect_list = list()
        effect_list.append(FlipVertical())

        if self.config['brightness'] != 1.0:
            if not 0.0 <= self.config['brightness'] <= 1.0:
                raise ValueError("DMD brightness value should be between 0.0 "
                                 "and 1.0. Yours is {}".format(self.config['brightness']))

            effect_list.append(Gain(gain=self.config['brightness']))

        self.effect_widget.effects = effect_list
        self.effect_widget.size = self.source.size

        self.fbo.add(self.effect_widget.canvas)

        self._set_dmd_fps()

    def _get_validated_config(self, config):
        raise NotImplementedError

    def _set_dmd_fps(self):
        # fps is the rate that the connected client requested. We'll use the
        # lower of the two

        mc_fps = self.config['fps']

        if mc_fps == 0:
            # pylint: disable-msg=protected-access
            mc_fps = Clock._max_fps

        # pylint: disable-msg=protected-access
        if mc_fps > Clock._max_fps:
            self.mc.log.warning("%s fps is higher than mpf-mc fps. "
                                "Will use mpf-mc fps setting for the DMD.",
                                PhysicalDmdBase.dmd_name_string)
            # pylint: disable-msg=protected-access
            fps = Clock._max_fps
            update = 0
        # pylint: disable-msg=protected-access
        elif Clock._max_fps > mc_fps > 0:
            fps = mc_fps
            update = 1 / fps
        else:
            # pylint: disable-msg=protected-access
            fps = Clock._max_fps
            update = 0

        Clock.schedule_interval(self.tick, update)
        self.mc.log.info("Setting %s to %sfps",
                         PhysicalDmdBase.dmd_name_string, fps)

    def tick(self, dt):
        """Draw image for DMD and send it."""
        del dt
        widget = self.source
        fbo = self.fbo

        # detach the widget from the parent
        parent = widget.parent
        if parent:
            parent.remove_widget(widget)

        self.effect_widget.add_widget(widget)

        # clear the fbo background
        fbo.bind()
        fbo.clear_buffer()
        fbo.release()

        fbo.draw()

        fbo.bind()
        data = glReadPixels(0, 0, widget.native_size[0], widget.native_size[1],
                            GL_RGB, GL_UNSIGNED_BYTE)
        fbo.release()

        # reattach to the parent
        if parent:
            self.effect_widget.remove_widget(widget)
            parent.add_widget(widget)

        if not self.config['only_send_changes'] or self.prev_data != data:
            self.prev_data = data
            self.send(data)

    def send(self, data):
        """Send data to DMD via BCP."""
        raise NotImplementedError


class PhysicalDmd(PhysicalDmdBase):

    """Physical monochrome DMD."""

    def _get_validated_config(self, config):
        return self.mc.config_validator.validate_config('physical_dmds', config)

    @classmethod
    def _convert_to_single_bytes(cls, data):
        new_data = bytearray()
        loops = 0

        for r, g, b in struct.iter_unpack('BBB', data):
            loops += 1
            try:
                pixel_weight = ((r * .299) + (g * .587) + (b * .114)) / 255.
                new_data.append(int(round(pixel_weight * 15)))

            except ValueError:
                raise ValueError(loops, r, g, b)

        return bytes(new_data)

    def send(self, data):
        """Send data to DMD via BCP."""
        data = self._convert_to_single_bytes(data)

        self.mc.bcp_processor.send('dmd_frame', rawbytes=data, name=self.name)


class PhysicalRgbDmd(PhysicalDmdBase):

    """Physical RGB DMD."""

    dmd_name_string = 'Physical RGB DMD'

    def _get_validated_config(self, config):
        return self.mc.config_validator.validate_config('physical_rgb_dmds',
                                                        config)

    def send(self, data):
        """Send data to DMD via BCP."""
        self.mc.bcp_processor.send('rgb_dmd_frame', rawbytes=data, name=self.name)


class FlipVertical(EffectBase):
    """GLSL effect to veritically flip a texture"""

    def __init__(self):
        super().__init__()

        self.glsl = '''

        vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)

        {{
        return texture2D(texture, vec2(tex_coords.x, 1.0 - tex_coords.y));
        }}
        '''