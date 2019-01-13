"""Base class for remote config players."""
import abc

from mpf.config_players.device_config_player import DeviceConfigPlayer


# pylint: disable-msg=abstract-method
class McConfigPlayer(DeviceConfigPlayer, metaclass=abc.ABCMeta):

    """Remote config player which is triggered via BCP."""

    config_file_section = None
    show_section = None
    machine_collection_name = None

    def __repr__(self):
        return 'McConfigPlayer.{}'.format(self.show_section)

    def _initialise_system_wide(self, **kwargs):
        del kwargs
        # this does not call super() since the base class uses self.config
        # and the mc uses self.machine_config
        if self.machine_collection_name:
            self.device_collection = getattr(self.machine,
                                             self.machine_collection_name)
        else:
            self.device_collection = None

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

    def play_from_trigger(self, settings, context, priority, calling_context, **kwargs):
        """Call play from BCP trigger."""
        if context not in self.instances:
            self.instances[context] = dict()
        if self.config_file_section not in self.instances[context]:
            self.instances[context][self.config_file_section] = dict()

        self.play(settings=settings, context=context, calling_context=calling_context, priority=priority, **kwargs)

    def clear_from_trigger(self, context, **kwargs):
        """Call clear_context from BCP trigger."""
        del kwargs
        self.clear_context(context=context)
