from mpf.config_players.plugin_player import PluginPlayer
from mpf.core.config_validator import ConfigValidator
from mpf.core.utility_functions import Util


class MpfSlidePlayer(PluginPlayer):
    """Base class for part of the slide player which runs as part of MPF.

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF, not the mpf-mc. MPF finds this instance because the mpf-mc setup.py
    has the following entry_point configured:

        slide_player=mpfmc.config_players.slide_player:register_with_mpf

    """
    config_file_section = 'slide_player'
    show_section = 'slides'

    def _validate_config_item(self, device, device_settings):
        # device is slide name, device_settings
        dict_is_widgets = False

        # if settings is list, it's widgets
        if isinstance(device_settings, list):
            device_settings = dict(widgets=device_settings)

        # Now check to see if all the settings are valid
        # slide settings. If not, assume it's a single widget settings.
        if isinstance(device_settings, dict):

            for key in device_settings.keys():
                if key not in ConfigValidator.config_spec['slide_player']:
                    dict_is_widgets = True
                    break

            if dict_is_widgets:
                device_settings = dict(widgets=[device_settings])
        else:
            raise AssertionError("Settings in slide_player {} have to be dict.".format(device))

        # todo make transition manager validation static and use that here too

        device_settings = self.machine.config_validator.validate_config(
            'slide_player', device_settings)

        if 'transition' in device_settings:
            if not isinstance(device_settings['transition'], dict):
                device_settings['transition'] = dict(
                    type=device_settings['transition'])

            try:
                device_settings['transition'] = (
                    self.machine.config_validator.validate_config(
                        'transitions:{}'.format(
                        device_settings['transition']['type']),
                        device_settings['transition']))

            except KeyError:
                raise ValueError('transition: section of config requires a'
                                 ' "type:" setting')

        if 'widgets' in device_settings:
            device_settings['widgets'] = self.process_widgets(
                device_settings['widgets'])

        return_dict = dict()
        return_dict[device] = device_settings

        return return_dict

    def process_widgets(self, config):
        # config is localized to a specific widget section

        # This method is based on
        # mpfmc.core.config_collections.widget.Widget.process_config()

        # We can't use that one though because there are lots of other imports
        # that module does.

        # todo we could move that to a central location

        if isinstance(config, dict):
            config = [config]

        # Note that we don't reverse the order of the widgets here since
        # they'll be reversed when they're played

        widget_list = list()

        for widget in config:
            widget_list.append(self.process_widget(widget))

        return widget_list

    def process_widget(self, config):
        # config is localized widget settings

        config['_default_settings'] = list(config.keys())

        try:
            self.machine.config_validator.validate_config('widgets:{}'.format(
                config['type']).lower(), config, base_spec='widgets:common')
        except KeyError:
            raise KeyError("Slide config validation error. Something is "
                           "wrong here: {}".format(config))

        if 'animations' in config:
            config['animations'] = self.process_animations(
                config['animations'])

        else:
            config['animations'] = None

        return config

    def process_animations(self, config):
        # config is localized to the slide's 'animations' section

        for event_name, event_settings in config.items():

            # str means it's a list of named animations
            if isinstance(event_settings, str):
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

    def process_animation(self, config):
        # config is localized to a single animation's settings within a list

        # str means it's a named animation
        if isinstance(config, str):
            config = dict(named_animation=config)

        # dict is settings for an animation
        elif isinstance(config, dict):
            self.machine.config_validator.validate_config('widgets:animations',
                                                          config)

            if len(config['property']) != len(config['value']):
                raise ValueError('Animation "property" list ({}) is not the '
                                 'same length as the "end" list ({}).'.
                                 format(config['property'], config['end']))

        return config


player_cls = MpfSlidePlayer


def register_with_mpf(machine):
    return 'slide', MpfSlidePlayer(machine)
