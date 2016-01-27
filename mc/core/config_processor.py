"""Contains classes which are used to process config files for the media
controller.

"""
from kivy.graphics import (Rectangle, Triangle, Quad, Point, Mesh, Line,
                           BorderImage, Bezier, Ellipse)
from kivy.logger import Logger
from kivy.utils import get_color_from_hex
from mpf.system.config import CaseInsensitiveDict, Config as MpfConfig
from mpf.system.utility_functions import Util

from mc.uix.display import Display
from mc.uix.slide_frame import SlideFrame
from mc.widgets.image import ImageWidget
from mc.widgets.text import Text
from mc.widgets.video import VideoWidget

type_map = CaseInsensitiveDict(text=Text,
                               image=ImageWidget,
                               video=VideoWidget,
                               bezier=Bezier,
                               border=BorderImage,
                               ellipse=Ellipse,
                               line=Line,
                               mesh=Mesh,
                               point=Point,
                               quad=Quad,
                               rectangle=Rectangle,
                               triangle=Triangle,
                               slide_frame=SlideFrame)


class McConfig(MpfConfig):
    def __init__(self, machine):
        self.mc = machine
        self.system_config = self.mc.machine_config['mpf_mc']
        self.log = Logger

        self.machine_sections = dict(slides=self.process_slides,
                                     widgets=self.process_widgets,
                                     displays=self.process_displays,
                                     animations=self.process_animations)

        self.mode_sections = dict(slides=self.process_slides,
                                  widgets=self.process_widgets,
                                  animations=self.process_animations)

        # process mode-based and machine-wide configs
        self.register_load_methods()
        self.process_config_file(section_dict=self.machine_sections,
                                 config=self.mc.machine_config)

        if not self.mc.displays:
            Display.create_default_display(self.mc)

    def register_load_methods(self):
        for section in self.mode_sections:
            self.mc.mode_controller.register_load_method(
                    load_method=self.process_mode_config,
                    config_section_name=section, section=section)

    def process_config_file(self, section_dict, config):
        for section in section_dict:
            if section in section_dict and section in config:
                self.process_localized_config_section(config=config[section],
                                                      section=section)

    def process_mode_config(self, config, mode, mode_path, section):
        self.process_localized_config_section(config, section)

    def process_localized_config_section(self, config, section):

        config = self.machine_sections[section](config)

    def process_displays(self, config):
        # config is localized to 'displays' section
        for display, settings in config.items():
            self.mc.displays[display] = self.create_display(display, settings)

    def create_display(self, name, config):
        # config is localized display settings
        return Display(self.mc, name,
                       **self.process_config2('displays', config))

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
        self.process_config2('widgets:{}'.format(config['type']).lower(),
                             config)

        try:
            config['widget_cls'] = type_map[config['type']]
            del config['type']
        except KeyError:
            raise AssertionError('"{}" is not a valid MPF display widget type'
                                 .format(config['type']))

        if not mode:
            priority = 0
        else:
            priority = mode.priority

        try:
            config['priority'] += priority
        except (KeyError, TypeError):
            config['priority'] = priority

        if 'color' in config and config['color']:
            config['color'] = get_color_from_hex(config['color'])

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
            animation = self.process_config2('widgets:animations',
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
            config = self.process_config2(
                    'transitions:{}'.format(config['type']), config)
        except KeyError:
            raise ValueError('transition: section of config requires a '
                             '"type:" setting')

        return config
