from mpf.config_players.bcp_plugin_player import BcpPluginPlayer


class DisplayLightPlayer(BcpPluginPlayer):

    config_file_section = 'display_light_player'
    show_section = 'display_lights'

    def __init__(self, machine):
        super().__init__(machine)

        self.machine.events.add_handler("display_light_player_apply", self._apply_lights)

    def _apply_lights(self, context, element, values, **kwargs):
        del kwargs
        context_dict = self._get_instance_dict(context)
        if element not in context_dict:
            return

        # get delta to last frame for interframe interpolation
        last_frame = context_dict[element][0]
        current_frame = self.machine.clock.get_time()
        context_dict[element][0] = current_frame

        priority = context_dict[element][1]

        key = "display_light_player_{}".format(element)
        fade_ms = int((current_frame - last_frame) * 1000)
        for light, color in values.items():
            if color == -1:
                self.machine.lights[light].remove_from_stack_by_key(key=key, fade_ms=fade_ms)
            else:
                self.machine.lights[light].color(key=key, color=color, priority=priority, fade_ms=fade_ms)

    def _validate_config_item(self, device, device_settings):
        device_settings = super()._validate_config_item(device, device_settings)

        for device, settings in device_settings.items():
            settings['light_map'] = self._build_light_map(settings['lights'])

        return device_settings

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Trigger remote player via BCP."""
        context_dict = self._get_instance_dict(context)

        for element, s in settings.items():
            if s['action'] == "play":
                context_dict[element] = [self.machine.clock.get_time(), priority]
            elif s['action'] == "stop":
                try:
                    del context_dict[element]
                except IndexError:
                    pass
                self._clear_key_from_lights(element)
            else:
                raise AssertionError("Invalid action {}".format(s['action']))

        super().play(settings, context, calling_context, priority, **kwargs)

    def _clear_key_from_lights(self, element):
        # remove color from leds
        key = "display_light_player_{}".format(element)
        for light in self.machine.lights.values():
            light.remove_from_stack_by_key(key=key)

    def _build_light_map(self, tags):
        light_map = []
        for tag in tags:
            lights = self.machine.lights.items_tagged(tag) if tag != '*' else self.machine.lights
            for light in lights:
                if not light.config['x'] or not light.config['y']:
                    continue
                if light.config['x'] < 0 or light.config['x'] > 1.0:
                    raise AssertionError("x needs to be between 0 and 1 for light {}".format(light.name))
                if light.config['y'] < 0 or light.config['y'] > 1.0:
                    raise AssertionError("y needs to be between 0 and 1 for light {}".format(light.name))

                light_map.append((light.config['x'], light.config['y'], light.name))

        return light_map

    def clear_context(self, context):
        """Clean up all active lights."""
        context_dics = self._get_instance_dict(context)
        for element in context_dics:
            self._clear_key_from_lights(element)

        self._reset_instance_dict(context)

        super().clear_context(context)


def register_with_mpf(machine):
    """Register widget player in MPF module."""
    return 'display_light', DisplayLightPlayer(machine)


player_cls = DisplayLightPlayer
