from mpf.core.config_player import ConfigPlayer


class McConfigPlayer(ConfigPlayer):
    config_file_section = None
    show_section = None
    machine_collection_name = None

    show_players = dict()
    config_file_players = dict()

    def __init__(self, machine):
        from kivy.logger import Logger
        super().__init__(machine)

    def __repr__(self):
        return 'McConfigPlayer.{}'.format(self.show_section)

    def _initialize(self):
        if self.machine_collection_name:
            self.device_collection = getattr(self.machine,
                                             self.machine_collection_name)
        else:
            self.device_collection = None

        self.machine.mode_controller.register_load_method(
                self.process_mode_config, self.config_file_section)

        # Look through the machine config for config_player sections and
        # for shows to validate and process
        if (self.config_file_section in self.machine.machine_config and
                    self.machine.machine_config[self.config_file_section]):
            # Validate
            self.machine.machine_config[self.config_file_section] = (
                self.validate_config(
                    self.machine.machine_config[self.config_file_section]))

            self.register_player_events(
                self.machine.machine_config[self.config_file_section])

        self.machine.events.add_handler(
            event='{}_play'.format(self.show_section),
            handler=self.play_from_trigger)

    def play_from_trigger(self, **kwargs):
        self.play(settings=kwargs)
