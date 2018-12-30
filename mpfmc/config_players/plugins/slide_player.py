from copy import deepcopy
from mpf.config_players.plugin_player import PluginPlayer
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

    __slots__ = ["slides"]

    def __init__(self, machine):
        """Initialise slide player."""
        super().__init__(machine)
        self.slides = None

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Process a slide_player event."""
        instance_dict = self._get_instance_dict(context)
        full_context = self._get_full_context(context)
        settings = deepcopy(settings)

        self.machine.log.info("SlidePlayer: Play called with settings=%s", settings)

        settings = settings['slides'] if 'slides' in settings else settings

        for slide, s in settings.items():
            slide_dict = self.machine.placeholder_manager.parse_conditional_template(slide)

            if slide_dict["condition"] and not slide_dict["condition"].evaluate(kwargs):
                continue
            slide = slide_dict["name"]

            s.update(kwargs)

            if s["slide"]:
                slide = s['slide']
            elif slide == "widgets":
                # name of anonymous slides depends on context + event name
                slide = "{}-{}".format(full_context, calling_context)

            try:
                s['priority'] += priority
            except (KeyError, TypeError):
                s['priority'] = priority

            if s['target']:
                target_name = s['target']
            else:
                target_name = 'default'

            if target_name not in self.machine.targets or not self.machine.targets[target_name].ready:
                # Target does not exist yet or is not ready. Perform action when it is ready
                raise AssertionError("Target {} not ready".format(target_name))

            #target = self.machine.targets[target_name]

            # remove target
            s.pop("target")

            if target_name not in instance_dict:
                instance_dict[target_name] = {}

            if s['action'] == 'play':
                # remove slide if it already exists
                if slide in instance_dict[target_name]:
                    instance_dict[target_name][slide].remove()
                    del instance_dict[target_name][slide]

                self.machine.log.debug("SlidePlayer: Playing slide '%s' on target '%s' (Args=%s)",
                                       slide,
                                       target_name,
                                       s)
                # is this a named slide, or a new slide?
                if 'widgets' in s:
                    self.bcp_client.send("slide_create", key=full_context,
                                              slide_name=slide, config=s["widgets"])
                    self.bcp_client.send("slide_show", key=full_context,
                                         slide_name=slide, config=s)
                else:
                    self.bcp_client.send("slide_show", key=full_context,
                                         slide_name=slide, config=s)

                # TODO: move to MC
                #target.get_screen(slide).on_slide_play()

                instance_dict[target_name][slide] = target.get_slide(slide)

            elif s['action'] == 'remove' and slide in instance_dict[target_name]:
                del instance_dict[target_name][slide]
                self.bcp_client.send("slide_remove", slide=slide,
                                    transition_config=s['transition'] if 'transition' in s else [])

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
