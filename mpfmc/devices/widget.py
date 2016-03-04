from collections import namedtuple

from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.utility_functions import Util

from mpfmc.core.device import Device

from mpfmc.uix.slide_frame import SlideFrame
from mpfmc.widgets.image import ImageWidget
from mpfmc.widgets.text import Text
from mpfmc.widgets.video import VideoWidget
from mpfmc.widgets.line import Line
from mpfmc.widgets.triangle import Triangle
from mpfmc.widgets.quad import Quad
from mpfmc.widgets.rectangle import Rectangle
from mpfmc.widgets.ellipse import Ellipse
from mpfmc.widgets.bezier import Bezier
from mpfmc.widgets.point import Point
from mpfmc.widgets.dmd import Dmd, ColorDmd
from mpfmc.widgets.character_picker import CharacterPicker
from mpfmc.widgets.entered_chars import EnteredChars

WidgetDevice = namedtuple('WidgetDevice',
                          'widgets tags label mode',
                          verbose=False)

class Widget(Device):

    config_section = 'widgets'
    collection = 'widgets'
    class_label = 'WidgetConfig'

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
                                   color_dmd=ColorDmd,
                                   character_picker=CharacterPicker,
                                   entered_chars=EnteredChars)

    @classmethod
    def process_config(cls, config):
        # config is localized to a specific widget section
        if isinstance(config, dict):
            config = [config]

        config.reverse()

        widget_list = list()

        for widget in config:
            widget_list.append(cls.process_widget(widget))

        return widget_list
        # config = dict(widgets=widget_list)
        # config['tags'] = []
        # config['mode'] = None
        # config['label'] = None
        # return WidgetDevice(**config)

    @classmethod
    def process_widget(cls, config, mode=None):
        # config is localized widget settings
        try:
            config['_widget_cls'] = Widget.type_map[config['type']]
        except KeyError:
            raise AssertionError('"{}" is not a valid MPF display widget type'
                                 .format(config['type']))

        config['_default_settings'] = set()

        for default_setting_name in config['_widget_cls'].merge_settings:
            if default_setting_name in config:
                config['_default_settings'].add(default_setting_name)

        cls.mc.config_validator.validate_config('widgets:{}'.format(
            config['type']).lower(),
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
            config['animations'] = cls.process_animations_from_slide_config(
                    config['animations'])

        else:
            config['animations'] = None

        return config

    @classmethod
    def process_animations_from_slide_config(cls, config):
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
                new_list.append(cls.process_animation(settings))

            config[event_name] = new_list

        return config

    @classmethod
    def process_animations(cls, config):
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
                new_list.append(cls.process_animation(s))

            config[name] = new_list

        # add this config to the global dict. We don't support having the same
        # named animation defined in multiple places, so we can blindly update.
        cls.mc.animation_configs.update(config)
        config = None

    @classmethod
    def process_animation(cls, config, mode=None):
        # config is localized to a single animation's settings within a list

        # str means it's a named animation
        if type(config) is str:
            config = dict(named_animation=config)

        # dict is settings for an animation
        elif type(config) is dict:
            animation = cls.mc.config_validator.validate_config(
                'widgets:animations',
                                             config)

            if len(config['property']) != len(config['value']):
                raise ValueError('Animation "property" list ({}) is not the '
                                 'same length as the "end" list ({'
                                 '}).'.format(config['property'], config[
                                 'end']))

        return config

    @classmethod
    def process_text_styles(cls, config):
        # config is localized to the 'text_styles' section
        for name, settings in config.items():
            cls.process_text_style(settings)

        return config

    @classmethod
    def process_text_style(cls, config):
        cls.mc.config_validator.validate_config('text_styles', config,
                                                      add_missing_keys=False)

        return config
