"""Contains classes which are used to process config files for the media
controller.

"""

from kivy.logger import Logger
from kivy.utils import get_color_from_hex
from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.config_processor import ConfigProcessorBase
from mpf.core.rgb_color import named_rgb_colors
from mpf.core.utility_functions import Util

from mc.uix.display import Display
from mc.uix.slide_frame import SlideFrame
from mc.widgets.image import ImageWidget
from mc.widgets.text import Text
from mc.widgets.video import VideoWidget
from mc.widgets.line import Line
from mc.widgets.triangle import Triangle
from mc.widgets.quad import Quad
from mc.widgets.rectangle import Rectangle
from mc.widgets.ellipse import Ellipse
from mc.widgets.bezier import Bezier
from mc.widgets.point import Point
from mc.widgets.dmd import Dmd, ColorDmd

type_map = CaseInsensitiveDict(text=Text,
                               image=ImageWidget,
                               video=VideoWidget,
                               slide_frame=SlideFrame,
                               bezier=Bezier,
                               # imageborder=Shape,
                               ellipse=Ellipse,
                               line=Line,
                               point=Point,
                               points=Point,
                               quad=Quad,
                               rectangle=Rectangle,
                               triangle=Triangle,
                               dmd=Dmd,
                               color_dmd=ColorDmd)


class ConfigProcessor(ConfigProcessorBase):
    def __init__(self, machine):
        self.mc = machine
        self.machine = machine
        self.system_config = self.mc.machine_config['mpf_mc']
        self.log = Logger
        self.machine_sections = None
        self.mode_sections = None

        self.machine_sections = dict(slides=self.process_slides,
                                     widgets=self.process_widgets,
                                     # displays=self.process_displays,
                                     animations=self.process_animations,
                                     text_styles=self.process_text_styles)

        self.mode_sections = dict(slides=self.process_slides,
                                  widgets=self.process_widgets,
                                  animations=self.process_animations,
                                  text_styles=self.process_text_styles)

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
            **self.machine.config_validator.process_config2('displays',
                                                            config))

    def process_slides(self, config):
        # config is localized to 'slides' section
        for slide_name in config:
            config[slide_name] = self.process_slide(config[slide_name])

        self.mc.slide_configs.update(config)
        config = None

    def process_slide(self, config):
        # config is localized to an single slide name entry
        if isinstance(config, dict):
            config = [config]

        for widget in config:

            # since dict is mutable it updates in place
            self.process_widget(widget)

        return config

    def process_widgets(self, config):
        # config is localized to 'widgets' section
        for widget_name, widget_settings in config.items():

            if isinstance(widget_settings, dict):
                widget_settings = [widget_settings]
            else:
                widget_settings.reverse()

            widget_list = list()

            for widget in widget_settings:
                widget_list.append(self.process_widget(widget))

            config[widget_name] = widget_list

        self.mc.widget_configs.update(config)
        config = None

    def process_widget(self, config, mode=None):
        # config is localized widget settings

        try:
            config['_widget_cls'] = type_map[config['type']]
        except KeyError:
            raise AssertionError('"{}" is not a valid MPF display widget type'
                                 .format(config['type']))

        config['_default_settings'] = set()

        for default_setting_name in config['_widget_cls'].merge_settings:
            if default_setting_name in config:
                config['_default_settings'].add(default_setting_name)

        self.machine.config_validator.process_config2('widgets:{}'.format(config['type']).lower(),
                             config, base_spec='widgets:common')

        if not mode:
            priority = 0
        else:
            priority = mode.priority

        try:
            config['priority'] += priority
        except (KeyError, TypeError):
            config['priority'] = priority

        if 'animations' in config:
            config['animations'] = self.process_animations_from_slide_config(
                    config['animations'])

        else:
            config['animations'] = None

        return config

    def process_animations_from_slide_config(self, config):
        # config is localized to the slide's 'animations' section

        for event_name, event_settings in config.items():

            # str means it's a list of named animations
            if type(event_settings) is str:
                event_settings = Util.string_to_list(event_settings)

            # dict means it's a single set of settings for one animation step
            elif isinstance(event_settings, dict):
                event_settings = [event_settings]

            # ultimately we're producing a list of dicts, so build that list
            # as we iterate
            new_list = list()
            for settings in event_settings:
                new_list.append(self.process_animation(settings))

            config[event_name] = new_list

        return config

    def process_animations(self, config):
        # processes the 'animations' section of a config file to populate the
        # mc.animation_configs dict.

        # config is localized to 'animations' section

        for name, settings in config.items():
            # if a named animation's settings are dict, that means there's just
            # a single step. We need a list
            if type(settings) is not list:
                settings = [settings]

            # iterate and build our final processed list
            new_list = list()
            for s in settings:
                new_list.append(self.process_animation(s))

            config[name] = new_list

        # add this config to the global dict. We don't support having the same
        # named animation defined in multiple places, so we can blindly update.
        self.mc.animation_configs.update(config)
        config = None

    def process_animation(self, config, mode=None):
        # config is localized to a single animation's settings within a list

        # str means it's a named animation
        if type(config) is str:
            config = dict(named_animation=config)

        # dict is settings for an animation
        elif type(config) is dict:
            animation = self.machine.config_validator.process_config2('widgets:animations',
                                             config)

            if len(config['property']) != len(config['value']):
                raise ValueError('Animation "property" list ({}) is not the '
                                 'same length as the "end" list ({'
                                 '}).'.format(config['property'], config[
                                 'end']))

        return config

    def process_transition(self, config):
        # config is localized to the 'transition' section
        try:
            config = self.machine.config_validator.process_config2(
                    'transitions:{}'.format(config['type']), config)
        except KeyError:
            raise ValueError('transition: section of config requires a '
                             '"type:" setting')

        return config

    def process_text_styles(self, config):
        # config is localized to the 'text_styles' section
        for name, settings in config.items():
            self.process_text_style(settings)

        return config

    def process_text_style(self, config):
        self.machine.config_validator.process_config2('text_styles', config,
                                                      add_missing_keys=False)

        return config

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
