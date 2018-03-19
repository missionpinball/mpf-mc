from copy import deepcopy
from importlib import import_module
import logging

from mpf.core.case_insensitive_dict import CaseInsensitiveDict


class ConfigCollection(dict):
    """ A lightweight collection of validated configs from the machine or
    mode config. Used to hold configs for things like slides, widgets,
    animations, widget_styles, etc.

    Getter attributes and methods automatically return a deepcopied version of
    the config dict.

    """

    config_section = None
    """Name of the section of the config file that holds this class's configs.
    """

    collection = None
    """Name of the mc attribute that will be used to hold these configs."""

    class_label = None
    """Friendly name for this collection which will be used in logs."""

    def __getattr__(self, attr):
        return self[attr]

    def __init__(self, mc):
        super().__init__()
        self.mc = mc
        self.log = logging.getLogger(self.class_label)

        self.mc.events.add_handler('init_phase_1',
                                   self.create_entries_from_root_config)

        self.mc.mode_controller.register_load_method(
            self.create_entries, self.config_section)

        self._initialize()

    def _initialize(self):
        pass

    def create_entries_from_root_config(self, **kwargs):
        del kwargs
        if self.config_section in self.mc.machine_config:
            self.create_entries(self.mc.machine_config[self.config_section])

    def create_entries(self, config, **kwargs):
        # config is localized to this collection's section
        del kwargs

        for name, settings in config.items():
            # if not settings:
            #     raise AssertionError("{} entry '{}' has an empty config."
            #                          .format(self.config_section, name))

            self[name] = self.process_config(settings)

    def process_config(self, config):
        raise NotImplementedError


def create_config_collections(mc, collections):

    for module in collections.values():
        imported_module = import_module(module)
        setattr(mc, imported_module.collection_cls.collection,
                imported_module.collection_cls(mc))
