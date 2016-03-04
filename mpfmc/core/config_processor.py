"""Contains classes which are used to process config files for the media
controller.

"""

from kivy.logger import Logger
from kivy.utils import get_color_from_hex
from mpf.core.config_processor import ConfigProcessorBase
from mpf.core.rgb_color import named_rgb_colors
from mpf.core.utility_functions import Util
from mpfmc.uix.display import Display


class ConfigProcessor(ConfigProcessorBase):
    def __init__(self, machine):
        self.mc = machine
        self.machine = machine
        self.system_config = self.mc.machine_config['mpf-mc']
        self.log = Logger
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
        return Display(self.mc, name,
            **self.machine.config_validator.validate_config('displays',
                                                            config))

    def color_from_string(self, color_string):
        if not color_string:
            return None

        color_string = str(color_string)

        if color_string in named_rgb_colors:
            color = list(named_rgb_colors[color_string])

        elif Util.is_hex_string(color_string):
            return get_color_from_hex(color_string)

        else:
            color = Util.string_to_list(color_string)
            if len(color) < 3:
                pass  # todo error?

        if len(color) == 3:
            color += [255]

        for i, x in enumerate(color):
            color[i] = int(x)/255

        return color
