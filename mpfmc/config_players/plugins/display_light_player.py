from mpf.config_players.bcp_plugin_player import BcpPluginPlayer


class DisplayLightPlayer(BcpPluginPlayer):

    config_file_section = 'display_light_player'
    show_section = 'display_lights'

    def __init__(self, machine):
        super().__init__(machine)

        self.machine.events.add_handler("display_light_player_apply", self._apply_lights)

    def _apply_lights(self, element, values, **kwargs):
        del kwargs
        key = "display_light_player_{}".format(element)
        for light, color in values.items():
            self.machine.lights[light].color(key=key, color=color)

    def _validate_config_item(self, device, device_settings):
        device_settings = super()._validate_config_item(device, device_settings)

        for device, settings in device_settings.items():
            light_map = []
            for tag in settings['lights']:
                for light in self.machine.lights.items_tagged(tag):
                    light_map.append((light.config['x'], light.config['y'], light.name))

            settings['light_map'] = light_map

        return device_settings

    def get_express_config(self, value):
        pass


def register_with_mpf(machine):
    """Register widget player in MPF module."""
    return 'display_light', DisplayLightPlayer(machine)


player_cls = DisplayLightPlayer