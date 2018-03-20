import abc


class BcpConfigPlayer(metaclass=abc.ABCMeta):

    """Base class for bcp players which play based on BCP."""

    config_file_section = None          # type: str
    show_section = None                 # type: str
    machine_collection_name = None      # type: str

    def __init__(self, machine):
        self.machine = machine
        self.instances = dict()
        self.instances['_global'] = dict()

        self.machine.events.add_handler(
            event='{}_play'.format(self.show_section),
            handler=self.play_from_trigger)

        self.machine.events.add_handler(
            event='{}_clear'.format(self.show_section),
            handler=self.clear_from_trigger)

    def _get_full_context(self, context):
        return context + "." + self.config_file_section

    def _get_instance_dict(self, context):
        return self.instances[context]

    def _reset_instance_dict(self, context):
        self.instances[context] = dict()

    def __repr__(self):
        return 'BcpConfigPlayer.{}'.format(self.show_section)

    def play_from_trigger(self, settings, context, priority, **kwargs):
        """Call play from BCP trigger."""
        if context not in self.instances:
            self.instances[context] = dict()

        self.play_element(settings=settings, context=context, priority=priority, **kwargs)

    def clear_from_trigger(self, context, **kwargs):
        """Call clear_context from BCP trigger."""
        del kwargs
        self.clear_context(context=context)

    # pylint: disable-msg=too-many-arguments
    @abc.abstractmethod
    def play_element(self, settings, element, context, calling_context, priority=0, **kwargs):
        """Directly play player."""
        # **kwargs since this is an event callback
        raise NotImplementedError

    @abc.abstractmethod
    def clear_context(self, context):
        """Clear the context."""
        raise NotImplementedError
