"""Contains classes which are used to process config files for the media
controller.

"""
from kivy.graphics import (Rectangle, Triangle, Quad, Point, Mesh, Line,
                           BorderImage, Bezier, Ellipse)
from kivy.logger import Logger
from kivy.uix.video import Video
from kivy.utils import get_color_from_hex
from mc.widgets.image import Image
from mc.widgets.text import Text
from mpf.system.config import CaseInsensitiveDict, Config as MpfConfig

type_map = CaseInsensitiveDict(text=Text,
                               image=Image,
                               video=Video,
                               bezier=Bezier,
                               border=BorderImage,
                               ellipse=Ellipse,
                               line=Line,
                               mesh=Mesh,
                               point=Point,
                               quad=Quad,
                               rectangle=Rectangle,
                               triangle=Triangle)


class McConfig(MpfConfig):
    def __init__(self, machine):
        self.mc = machine
        self.system_config = self.mc.machine_config['mpf-mc']
        self.log = Logger

        self.sections = dict(screens=self.process_screens,
                             widgets=self.process_widgets)

        # process mode-based and machine-wide configs
        self.register_load_methods()
        self.process_config_file(config=self.mc.machine_config)

    def register_load_methods(self):
        for section in self.sections:
            self.mc.mode_controller.register_load_method(
                    load_method=self.process_mode_config,
                    config_section_name=section, section=section)

    def process_config_file(self, config):
        for section in self.sections:
            try:
                self.process_localized_config_section(config=config[section],
                                                      section=section)
            except KeyError:
                pass

    def process_mode_config(self, config, mode_path, section):
        self.process_localized_config_section(config, section)

    def process_localized_config_section(self, config, section):
        config = self.sections[section](config)

    def process_screens(self, config):
        # config is localized to 'screens' section
        for screen_name in config:
            config[screen_name] = self.process_screen(config[screen_name])

        return config

    def process_screen(self, config):
        # config is localized to an single screen name entry
        if isinstance(config, dict):
            config = [config]

        else:
            config.reverse()

        for widget in config:
            widget = self.process_widget(widget)

        # TODO add the display to this processed config

        return config

    def process_widgets(self, config):
        # config is localized to 'widgets' section
        for widget_name, widget_settings in config.items():

            if isinstance(widget_settings, dict):
                widget_settings = [widget_settings]
            else:
                widget_settings.reverse()

            for widget in widget_settings:
                widget = self.process_widget(widget)

        return config

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

        config['mode'] = mode

        if 'color' in config:
            config['color'] = get_color_from_hex(config['color'])

        # validate_widget(config)

        config['_parsed_'] = True

        if 'v_pos' not in config:
            config['v_pos'] = 'center'
        if 'h_pos' not in config:
            config['h_pos'] = 'center'
        if 'x' not in config:
            config['x'] = 0
        if 'y' not in config:
            config['y'] = 0

        return config

    def validate_widget(self, config):
        config['widget_cls'](mc=None, **config)
        return
