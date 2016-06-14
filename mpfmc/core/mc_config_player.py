"""Base class for remote config players."""
from mpf.core.config_player import ConfigPlayer


class McConfigPlayer(ConfigPlayer):

    """Remote config player which is triggered via BCP."""

    config_file_section = None
    show_section = None
    machine_collection_name = None

    show_players = dict()
    config_file_players = dict()

    def __init__(self, machine):
        super().__init__(machine)

    def __repr__(self):
        return 'McConfigPlayer.{}'.format(self.show_section)

    def _initialize(self):
        # this does not call super() since the base class uses self.config
        # and the mc uses self.machine_config
        if self.machine_collection_name:
            self.device_collection = getattr(self.machine,
                                             self.machine_collection_name)
        else:
            self.device_collection = None

        self.instances['_global'][self.config_file_section] = dict()

        self.machine.mode_controller.register_load_method(
            self.process_mode_config, self.config_file_section)

        self.machine.mode_controller.register_start_method(
            self.mode_start, self.config_file_section)

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

        self.machine.events.add_handler(
            event='{}_clear'.format(self.show_section),
            handler=self.clear_from_trigger)

    def play_from_trigger(self, settings, context, priority, **kwargs):
        """Call play from BCP trigger."""
        if context not in self.instances:
            self.instances[context] = dict()
        if self.config_file_section not in self.instances[context]:
            self.instances[context][self.config_file_section] = dict()

        self.play(settings=settings, context=context, priority=priority, **kwargs)

    def clear_from_trigger(self, context, **kwargs):
        """Call clear_context from BCP trigger."""
        del kwargs
        self.clear_context(context=context)
