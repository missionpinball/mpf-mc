"""Physical DMD"""
from kivy.clock import Clock
from kivy.graphics.fbo import Fbo
from kivy.graphics.opengl import glReadPixels, GL_RGB, GL_UNSIGNED_BYTE
from kivy.graphics.texture import Texture
from kivy.uix.effectwidget import EffectWidget, EffectBase

from mpfmc.widgets.dmd import Gain


class PhysicalDmdBase(object):
    dmd_name_string = 'Physical DMD'

    def __init__(self, mc, config, fps):
        self.mc = mc
        self.config = (self.mc.config_validator.validate_config('physical_dmd',
                                                                config))

        self.source = self.mc.displays[self.config['source_display']]
        self.prev_data = None

        # put the widget canvas on a Fbo
        texture = Texture.create(size=self.source.size, colorfmt='rgb')
        self.fbo = Fbo(size=self.source.size, texture=texture)

        self.effect_widget = EffectWidget()

        effect_list = list()
        effect_list.append(FlipVertical())
        effect_list.append(Gain(gain=0.3))
        self.effect_widget.effects = effect_list

        self._set_dmd_fps(fps)

    def _set_dmd_fps(self, fps):
        # fps is the rate that the connected client requested. We'll use the
        # lower of the two

        fps = int(fps)
        mc_fps = self.config['fps']

        if mc_fps == 0:
            mc_fps = Clock._max_fps

        if fps < mc_fps:
            self.log.info("MPF DMD requested frame rate of %sfps, so that will"
                          "be used instead of the configured setting of %s",
                          fps, mc_fps)
            mc_fps = fps

        if mc_fps > Clock._max_fps:
            self.mc.log.warning("%s fps is higher than mpf-mc fps. "
                                "Will use mpf-mc fps setting for the DMD.",
                                PhysicalDmdBase.dmd_name_string)
            fps = Clock._max_fps
            update = 0
        elif Clock._max_fps > mc_fps > 0:
            fps = mc_fps
            update = 1 / fps
        else:
            fps = Clock._max_fps
            update = 0

        Clock.schedule_interval(self.tick, update)
        self.mc.log.info("Setting %s to %sfps",
                         PhysicalDmdBase.dmd_name_string, fps)

    def tick(self, dt):
        del dt
        widget = self.source
        fbo = self.fbo

        # detach the widget from the parent
        parent = widget.parent
        if parent:
            parent.remove_widget(widget)

        self.effect_widget.add_widget(widget)

        fbo.add(self.effect_widget.canvas)

        # todo something is slow here. Quick tests show it might be binding and
        # releasing the FBO. Maybe move this to its own thread? Need to
        # experiment more.

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
        raise NotImplementedError


class PhysicalDmd(PhysicalDmdBase):

    def send(self, data):
        self.mc.bcp_processor.send('dmd_frame', rawbytes=data)


class PhysicalRgbDmd(PhysicalDmdBase):

    dmd_name_string = 'Physical RGB DMD'

    def send(self, data):
        self.mc.bcp_processor.send('rgb_dmd_frame', rawbytes=data)


class FlipVertical(EffectBase):
    """GLSL effect to veritically flip a texture"""

    def __init__(self):
        super().__init__()

        # todo I have no idea why we need to use the value of 0.32 below. I
        # thave to test to see if that's always the case or varies depending
        # on screen size.

        self.glsl = '''

        vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)

        {{
        return texture2D(texture, vec2(tex_coords.x, .32 - tex_coords.y));
        }}
        '''