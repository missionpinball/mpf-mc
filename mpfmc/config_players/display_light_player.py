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
        self._last_color = {}

    def play_element(self, settings, element, context, calling_context, priority=0, **kwargs):
        context_dict = self._get_instance_dict(context)
        if settings['action'] == "play":
            if not self._scheduled:
                self._scheduled = True
                Clock.schedule_interval(self._tick, 0)
            if element not in context_dict:
                context_dict[element] = self._setup_fbo(element, settings)
            else:
                context_dict[element][5] = True
        elif settings['action'] == "stop":
            try:
                context_dict[element][5] = False
            except IndexError:
                pass
        else:
            raise AssertionError("Unknown action {}".format(settings['action']))

    def _setup_fbo(self, element, settings):
        """Setup FBO for a display."""
        if element not in self.machine.displays:
            raise AssertionError("Display {} not found. Please create it to use display_light_player.".format(element))
        source = self.machine.displays[element]

        # put the widget canvas on a Fbo
        texture = Texture.create(size=source.size, colorfmt='rgb')
        fbo = Fbo(size=source.size, texture=texture)

        effect_widget = EffectWidget()

        effect_list = list()

        effect_widget.effects = effect_list
        effect_widget.size = source.size

        fbo.add(effect_widget.canvas)

        return [fbo, effect_widget, source, settings, True, True]

    def _tick(self, dt):
        del dt
        for context, instances in self.instances.items():
            for element, instance in instances.items():
                if not element[5]:
                     continue
                self._render(instance, element, context)

    def _render(self, instance, element, context):
        fbo, effect_widget, source, settings, first, enabled = instance
        instance[4] = False

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

        if not first:
            # for some reasons we got garbage in the first buffer. we just skip it for now
            values = {}
            width = source.native_size[0]
            height = source.native_size[1]
            for x, y, name in settings['light_map']:
                x_pixel = int(x * width)
                y_pixel = height - int(y * height)
                value = (
                    data[width * y_pixel * 3 + x_pixel * 3],
                    data[width * y_pixel * 3 + x_pixel * 3 + 1],
                    data[width * y_pixel * 3 + x_pixel * 3 + 2])

                if name not in self._last_color or self._last_color[name] != value:
                    self._last_color[name] = value
                    values[name] = value

            self.machine.bcp_processor.send("trigger", name="display_light_player_apply", context=context,
                                            values=values, element=element, _silent=True)
        # clear the fbo background
        fbo.bind()
        fbo.clear_buffer()
        fbo.release()

    def clear_context(self, context):
        self._reset_instance_dict(context)


mc_player_cls = McDisplayLightPlayer
