"""Base class used for things that "play" from the config files, such as
WidgetPlayer, SlidePlayer, etc."""


class ConfigPlayer(object):
    config_file_section = None

    def __init__(self, mc):
        self.mc = mc

        try:
            self.process_config(
                    self.mc.machine_config[self.config_file_section])
            self.register_player_events(
                    self.mc.machine_config[self.config_file_section])
        except KeyError:
            pass

        self.mc.mode_controller.register_load_method(
                self.process_config, self.config_file_section)

        self.mc.mode_controller.register_start_method(
                self.register_player_events, self.config_file_section)

    def process_config(self, config, **kwargs):
        # config is localized

        for event, settings in config.items():

            if isinstance(settings, dict):
                settings = [settings]

            final_settings = list()
            for these_settings in settings:

                s = self.mc.config_processor.process_config2(
                        self.config_file_section, these_settings)
                s = self.additional_processing(s)

                final_settings.append(s)

            config[event] = final_settings

    def register_player_events(self, config, mode=None, priority=0):
        # config is localized

        key_list = list()

        for event, settings in config.items():
            key_list.append(self.mc.events.add_handler(
                    event,
                    self.play,
                    mode=mode,
                    settings=settings))

        return self.unload_player_events, key_list

    def unload_player_events(self, key_list):
        self.mc.events.remove_handlers_by_keys(key_list)

    def additional_processing(self, config):
        return config

    def play(self, settings, mode=None):
        raise NotImplementedError
