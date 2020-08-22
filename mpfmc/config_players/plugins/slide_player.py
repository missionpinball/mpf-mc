from functools import partial

from mpf.config_players.plugin_player import PluginPlayer
from mpf.core.utility_functions import Util
from mpfmc.config_collections.animation import AnimationCollection
from mpfmc.uix.widget_magic_events import magic_events


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
                if key not in self.machine.config_validator.get_config_spec()['slide_player']:
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
                        'transitions:{}'.format(device_settings['transition']['type']), device_settings['transition']))

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

    def _register_trigger(self, event, **kwargs):
        """Register trigger via BCP for MC."""
        del kwargs
        client = self.machine.bcp.transport.get_named_client("local_display")
        if client:
            self.machine.bcp.interface.add_registered_trigger_event_for_client(client, event)
        else:
            self.machine.events.add_handler("bcp_clients_connected", partial(self._register_trigger, event))

    def process_widget(self, config):
        # config is localized widget settings

        config['_default_settings'] = list(config.keys())

        try:
            self.machine.config_validator.validate_config('widgets:{}'.format(
                config['type']).lower(), config, base_spec='widgets:common')
        except KeyError:
            raise KeyError("Slide config validation error. Something is "
                           "wrong here: {}".format(config))

        if 'control_events' in config:
            for event_dict in config['control_events']:
                if event_dict["event"] not in magic_events:
                    self._register_trigger(event_dict["event"])

        if 'reset_animations_events' in config:
            for event_name in config['reset_animations_events']:
                if event_name not in magic_events:
                    self._register_trigger(event_name)

        if 'animations' in config:
            config['animations'] = self.process_animations(
                config['animations'])

        else:
            config['animations'] = None

        return config

    def process_animations(self, config):
        # config is localized to the slide's 'animations' section

        for event_name, event_settings in config.items():

            # make sure the event_name is registered as a trigger event so MPF
            # will send those events as triggers via BCP. But we don't want
            # to register magic events since those aren't real MPF events.
            if event_name not in magic_events:
                self._register_trigger(event_name)

            # str means it's a list of named animations
            if isinstance(event_settings, str):
                event_settings = Util.string_to_event_list(event_settings)

            # dict means it's a single set of settings for one animation step
            elif isinstance(event_settings, dict):
                event_settings = [event_settings]

            # ultimately we're producing a list of dicts, so build that list
            # as we iterate
            new_list = list()
            for settings in event_settings:
                new_list.append(AnimationCollection.process_animation(settings, self.machine.config_validator))

            config[event_name] = new_list

        return config


player_cls = MpfSlidePlayer


def register_with_mpf(machine):
    return 'slide', MpfSlidePlayer(machine)
