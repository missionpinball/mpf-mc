"""Contains classes which are used to process config files for the media controller."""

from mpf.core.config_processor import ConfigProcessor as ConfigProcessorBase

# from mpfmc.uix.display import Display is imported deeper in this file
# we need it there because if we do a standard import, the Clock is created
# before we have a chance to read the config and set the maxfps


class ConfigProcessor(ConfigProcessorBase):

    """Reads the config for mc."""

    config_spec = None

    def __init__(self, machine):
        super().__init__(False, False)
        self.mc = machine
        self.machine = machine
        self.system_config = self.mc.machine_config['mpf-mc']
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
            # pylint: disable-msg=import-outside-toplevel
            from mpfmc.uix.display import Display
            Display.create_default_display(self.mc)

    def _init(self, **kwargs):
        del kwargs
        self.process_config_file(section_dict=self.machine_sections,
                                 config=self.mc.machine_config)

    def register_load_methods(self):
        """Register load method for modes."""
        for section in self.mode_sections:
            self.machine.mode_controller.register_load_method(
                load_method=self.process_mode_config,
                config_section_name=section, section=section)

    def process_config_file(self, section_dict, config):
        """Called to process a config file (can be a mode or machine config)."""
        for section in section_dict:
            if section in section_dict and section in config:
                self.process_localized_config_section(config=config[section],
                                                      section=section)

    def process_localized_config_section(self, config, section):
        """Process a single key within a config file.

        Args:
            config: The subsection of a config dict to process
            section: The name of the section, either 'scripts' or 'shows'.

        """
        self.machine_sections[section](config)

    def process_mode_config(self, config, mode, mode_path, section, **kwargs):
        """Process a mode config."""
        del mode
        del mode_path
        del kwargs
        self.process_localized_config_section(config, section)

    def process_displays(self, config):
        # config is localized to 'displays' section
        for display, settings in config.items():
            self.mc.displays[display] = self.create_display(display, settings)

    def create_display(self, name, config):
        # config is localized display settings
        # pylint: disable-msg=import-outside-toplevel
        from mpfmc.uix.display import Display
        return Display(self.mc, name, **self.machine.config_validator.validate_config('displays', config))
