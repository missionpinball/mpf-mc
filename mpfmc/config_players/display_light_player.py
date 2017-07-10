from kivy.clock import Clock
from kivy.graphics.fbo import Fbo
from kivy.graphics.opengl import glReadPixels, GL_RGB, GL_RGBA, GL_UNSIGNED_BYTE
from kivy.graphics.texture import Texture
from kivy.uix.effectwidget import EffectWidget

from mpfmc.core.bcp_config_player import BcpConfigPlayer


class McDisplayLightPlayer(BcpConfigPlayer):

    """Grabs pixel from a display and use them as lights."""

    config_file_section = 'display_light_player'
    show_section = 'display_lights'
    machine_collection_name = 'displays'

    def __init__(self, machine):
        super().__init__(machine)
        self._scheduled = False

    def play_element(self, settings, element, context, calling_context, priority=0, **kwargs):
        context_dict = self._get_instance_dict(context)
        if settings['action'] == "play":
            if not self._scheduled:
                self._scheduled = True
                Clock.schedule_interval(self._tick, 0)
            context_dict[element] = self._setup_fbo(element, settings)

    def _setup_fbo(self, element, settings):
        """Setup FBO for a display."""
        source = self.machine.displays[element]

        # put the widget canvas on a Fbo
        texture = Texture.create(size=source.size, colorfmt='rgb')
        fbo = Fbo(size=source.size, texture=texture)

        effect_widget = EffectWidget()

        effect_list = list()

        effect_widget.effects = effect_list
        effect_widget.size = source.size

        fbo.add(effect_widget.canvas)

        return (fbo, effect_widget, source, settings)

    def _tick(self, dt):
        del dt
        for context, instances in self.instances.items():
            for element, instance in instances.items():
                self._render(instance, element)

    def _render(self, instance, element):
        fbo, effect_widget, source, settings = instance

        # detach the widget from the parent
        parent = source.parent
        if parent:
            parent.remove_widget(source)

        effect_widget.add_widget(source)

        fbo.draw()

        fbo.bind()
        data = glReadPixels(0, 0, source.native_size[0], source.native_size[1],
                            GL_RGB, GL_UNSIGNED_BYTE)

        fbo.release()

        # reattach to the parent
        if parent:
            effect_widget.remove_widget(source)
            parent.add_widget(source)

        values = {}
        for x, y, name in settings['light_map']:
            values[name] = (
                data[source.native_size[0] * y * 3 + x * 3],
                data[source.native_size[0] * y * 3 + x * 3 + 1],
                data[source.native_size[0] * y * 3 + x * 3 + 2])

        self.machine.bcp_processor.send("trigger", name="display_light_player_apply", values=values, element=element)
        # clear the fbo background
        fbo.bind()
        fbo.clear_buffer()
        fbo.release()

    def clear_context_element(self, context, element):
        pass


mc_player_cls = McDisplayLightPlayer
