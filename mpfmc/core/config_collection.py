from importlib import import_module

from mpf.core.device_manager import DeviceCollection


class ConfigCollection(DeviceCollection):
    """ A lightweight collection of validated configs from the machine or
    mode config. Used to hold configs for things like slides, widgets,
    animations, widget_styles, etc.

    Getter attributes and methods automatically return a deepcopied version of
    the config dict.

    """

    __slots__ = []

    def __init__(self, machine, collection, config_section):
        super().__init__(machine, collection, config_section)
        self.machine.events.add_handler('init_phase_1',
                                        self.create_entries_from_root_config)

        self.machine.events.add_handler('init_phase_2',
                                        self.validate_entries_from_root_config)

        self.machine.mode_controller.register_load_method(
            self.create_entries, self.config_section, priority=100)

        self._initialize()

    @property
    def mc(self):
        return self.machine

    def _initialize(self):
        pass

    def create_entries_from_root_config(self, **kwargs):
        del kwargs
        if self.config_section in self.machine.machine_config:
            self.create_entries(self.machine.machine_config[self.config_section])

    def create_entries(self, config, **kwargs):
        # config is localized to this collection's section
        del kwargs

        for name, settings in config.items():
            # if not settings:
            #     raise AssertionError("{} entry '{}' has an empty config."
            #                          .format(self.config_section, name))

            self[name] = self.process_config(settings)

    def validate_entries_from_root_config(self, **kwargs):
        del kwargs
        if self.config_section in self.machine.machine_config:
            self.validate_entries(self.machine.machine_config[self.config_section])

    def validate_entries(self, config, **kwargs):
        del kwargs
        for name in config.keys():
            self.validate_config(self[name])

    def process_config(self, config):
        raise NotImplementedError

    def validate_config(self, config):
        pass


def create_config_collections(mc, collections):

    for module in collections.values():
        imported_module = import_module(module)
        setattr(mc, imported_module.collection_cls.collection,
                imported_module.collection_cls(mc, imported_module.collection_cls.collection,
                                               imported_module.collection_cls.collection))
