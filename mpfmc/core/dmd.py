"""DMD (hardware device)."""
import struct

from kivy.graphics.instructions import Callback
from kivy.uix.effectwidget import EffectWidget

from kivy.clock import Clock
from kivy.graphics.fbo import Fbo
from kivy.graphics.opengl import glReadPixels, GL_RGB, GL_UNSIGNED_BYTE
from kivy.graphics.texture import Texture

from mpfmc.effects.gain import GainEffect
from mpfmc.effects.flip_vertical import FlipVerticalEffect
from mpfmc.effects.gamma import GammaEffect

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc     # pylint: disable-msg=cyclic-import,unused-import


class DmdBase:
    """Base class for DMD devices."""

    dmd_name_string = 'DMD'

    def __init__(self, mc: "MpfMc", name: str, config: dict) -> None:
        """initialize DMD."""

        self.mc = mc
        self.name = name

        self.mc.log.info('Initializing DMD')

        self.config = self._get_validated_config(config)

        self.source = self.mc.displays[self.config['source_display']]
        self.prev_data = None
        self._dirty = True

        # put the widget canvas on a Fbo
        texture = Texture.create(size=self.source.size, colorfmt='rgb')
        self.fbo = Fbo(size=self.source.size, texture=texture)

        self.effect_widget = EffectWidget()

        effect_list = list()
        effect_list.append(FlipVerticalEffect())

        if self.config['brightness'] != 1.0:
            if not 0.0 <= self.config['brightness'] <= 1.0:
                raise ValueError("DMD brightness value should be between 0.0 "
                                 "and 1.0. Yours is {}".format(self.config['brightness']))

            effect_list.append(GainEffect(gain=self.config['brightness']))

        if self.config['gamma'] != 1.0:
            effect_list.append(GammaEffect(gamma=self.config['gamma']))

        self.effect_widget.effects = effect_list
        self.effect_widget.size = self.source.size

        self.fbo.add(self.effect_widget.canvas)

        with self.source.canvas:
            self.callback = Callback(self._trigger_rendering)

        self._set_dmd_fps()

    def _trigger_rendering(self, *args):
        del args
        self._dirty = True

    def _get_validated_config(self, config: dict) -> dict:
        raise NotImplementedError

    def _set_dmd_fps(self) -> None:
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
                                DmdBase.dmd_name_string)
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
                         DmdBase.dmd_name_string, fps)

    def tick(self, *args) -> None:
        """Draw image for DMD and send it."""
        del args
        # run this at the end of the tick to make sure all kivy bind callbacks have executed
        if self._dirty:
            Clock.schedule_once(self._render, -1)

    def _render(self, dt):
        del dt
        self._dirty = False
        widget = self.source
        fbo = self.fbo

        # detach the widget from the parent
        parent = widget.parent
        if parent and hasattr(parent, "remove_display_source"):
            parent.remove_display_source(widget)

        # clear the fbo background
        fbo.bind()
        fbo.clear_buffer()
        fbo.release()

        self.effect_widget.add_widget(widget.container)

        fbo.draw()

        fbo.bind()
        data = glReadPixels(0, 0, widget.native_size[0], widget.native_size[1],
                            GL_RGB, GL_UNSIGNED_BYTE)
        fbo.release()

        self.effect_widget.remove_widget(widget.container)

        # reattach to the parent
        if parent and hasattr(parent, "add_display_source"):
            parent.add_display_source(widget)

        if not self.config['only_send_changes'] or self.prev_data != data:
            self.prev_data = data
            self.send(data)

    def send(self, data: bytes) -> None:
        """Send data to DMD via BCP."""
        raise NotImplementedError


class Dmd(DmdBase):
    """Monochrome DMD."""

    def _get_validated_config(self, config: dict) -> dict:
        return self.mc.config_validator.validate_config('dmds', config)

    @classmethod
    def _convert_to_single_bytes(cls, data, config: dict) -> bytes:
        new_data = bytearray()
        loops = 0
        config.setdefault('luminosity', (.299, .587, .114))
        luminosity = config['luminosity']

        for r, g, b in struct.iter_unpack('BBB', data):
            loops += 1
            try:
                pixel_weight = ((r * luminosity[0]) + (g * luminosity[1]) + (b * luminosity[2])) / 255.
                new_data.append(int(round(pixel_weight * 15)))

            except ValueError:
                raise ValueError(loops, r, g, b)

        return bytes(new_data)

    def send(self, data: bytes) -> None:
        """Send data to DMD via BCP."""
        data = self._convert_to_single_bytes(data, self.config)

        self.mc.bcp_processor.send('dmd_frame', rawbytes=data, name=self.name)


class RgbDmd(DmdBase):
    """RGB DMD."""

    dmd_name_string = 'RGB DMD'

    def _get_validated_config(self, config: dict) -> dict:
        return self.mc.config_validator.validate_config('rgb_dmds', config)

    @staticmethod
    def _reorder_channels(data, order):
        new_data = bytearray()
        for r, g, b in struct.iter_unpack('BBB', data):
            for channel in order:
                if channel == "r":
                    new_data.append(r)
                elif channel == "g":
                    new_data.append(g)
                elif channel == "b":
                    new_data.append(b)
                else:
                    raise ValueError("Unknown channel {}".format(channel))

        return bytes(new_data)

    def send(self, data: bytes) -> None:
        """Send data to RGB DMD via BCP."""
        if self.config['channel_order'] != 'rgb':
            data = self._reorder_channels(data, self.config['channel_order'])
        self.mc.bcp_processor.send('rgb_dmd_frame', rawbytes=data, name=self.name)
