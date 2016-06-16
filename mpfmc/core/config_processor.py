"""Contains classes which are used to process config files for the media
controller.

"""

import logging
from mpf.core.config_processor import ConfigProcessor as ConfigProcessorBase

# from mpfmc.uix.display import Display is imported deeper in this file
# we need it there because if we do a standard import, the Clock is created
# before we have a chance to read the config and set the maxfps


class ConfigProcessor(ConfigProcessorBase):
    def __init__(self, machine):
        self.mc = machine
        self.machine = machine
        self.system_config = self.mc.machine_config['mpf-mc']
        self.log = logging.getLogger('ConfigProcessor')
        self.machine_sections = None
        self.mode_sections = None

        self.machine_sections = dict()
        self.mode_sections = dict()

        # process mode-based and machine-wide configs
        self.register_load_methods()

        self.mc.events.add_handler('init_phase_1', self._init)

        # todo need to clean this up
        try:
            self.process_displays(config=self.mc.machine_config['displays'])
        except KeyError:
            pass

        if not self.mc.displays:
            from mpfmc.uix.display import Display
            Display.create_default_display(self.mc)

    def _init(self):
        self.process_config_file(section_dict=self.machine_sections,
                                 config=self.mc.machine_config)

    def process_displays(self, config):
        # config is localized to 'displays' section
        for display, settings in config.items():
            self.mc.displays[display] = self.create_display(display, settings)

    def create_display(self, name, config):
        # config is localized display settings
        from mpfmc.uix.display import Display
        return Display(self.mc, name,
            **self.machine.config_validator.validate_config('displays',
                                                            config))
