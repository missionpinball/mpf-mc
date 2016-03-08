from copy import deepcopy

from mpf.config_players.plugin_player import PluginPlayer
from mpf.core.config_validator import ConfigValidator
from mpfmc.core.mc_config_player import McConfigPlayer


class MpfSlidePlayer(PluginPlayer):
    """Base class for the slide player which runs as part of MPF.

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF, not the mpf-mc. MPF finds this instance because the mpf-mc setup.py has the following
    entry_point configured:

        slide_player=mpfmc.config_players.slide_player:register_with_mpf

    """
    config_file_section = 'slide_player'
    show_section = 'slides'

    def play(self, settings, mode=None, **kwargs):
        super().play(settings, mode, **kwargs)


class McSlidePlayer(McConfigPlayer):
    """Base class for the Slide Player that runs on the mpf-mc side of things.
    It receives all of its instructions via BCP from a MpfSlidePlayer instance
    running as part of MPF.

    The slide_player: section of a config file (either the machine-wide or
    a mode-specific config) looks like this:

    slide_player:
        <event_name>:
            <slide_name>:
                <slide_settings>: ...

    The express config just puts a slide_name next to an event. (In this case
    it assumes the slide has already been defined in yours slides: section)

    slide_player:
        some_event: slide_name_to_show

    If you want to control other settings (such as a display target, priority,
    transition, etc.), enter the slide name on the next line and the settings
    indented under it, like this:

    slide_player:
        some_event:
            slide_name_to_show:
                target: dmd
                transition: fade

    Alternately you can pass a full configuration. You can also pass a widget
    or list of widgets to create the slide if based on the settings in the
    slide_player. Here are several various examples:

    slide_player:
        some_event:
            slide1:
                transition: move_in

        some_event2:
            slide2:
                transition:
                    type: move_in
                    direction: right
                    duration: 1s

        some_event3: slide3

        some_event4:
            slide4:
                type: text
                text: SOME TEXT
                color: red
                y: 50

        some_event5:
            slide5:
              - type: text
                text: SOME TEXT
                color: red
                y: 50
              - type: text
                text: AND MORE TEXT
                color: blue
                y: 150

        some_event6:
            slide6:
                widgets:
                - type: text
                  text: SOME TEXT
                  color: red
                  y: 50
                - type: text
                  text: AND MORE TEXT
                  color: blue
                  y: 150

        some_event7:
            slide7:
                widgets:
                - type: text
                  text: SOME TEXT
                  color: red
                  y: 50
                - type: text
                  text: AND MORE TEXT
                  color: blue
                  y: 150
                transition: move_in

    """
    config_file_section = 'slide_player'
    show_section = 'slides'
    machine_collection_name = 'slides'

    def play(self, settings, mode=None, caller=None, **kwargs):
        """Plays a validated slides: section from a slide_player: section of a
        config file or the slides: section of a show.

        The config must be validated. Validated config looks like this:

        <slide_name>:
            <settings>: ...

        <settings> can be:

        priority:
        show:
        force:
        target:
        widgets:
        transition:

        If widgets: is in the settings, a new slide will be created with the
        widgets from the settings. Otherwise it will assume the <slide_name> is
        the slide to show.

        """
        super().play(settings, mode, caller, **kwargs)

        # todo figure out where the settings are coming from and see if we can
        # move the deepcopy there?
        settings = deepcopy(settings)

        if 'slides' in settings:
            settings = settings['slides']

        for slide, s in settings.items():
            # figure out target first since we need that to make a slide

            try:
                target = self.machine.targets[s.pop('target')]
            except KeyError:
                if mode and mode.target:
                    target = mode.target
                else:
                    target = self.machine.targets['default']

            s.update(kwargs)  # need to mix-in any kwargs

            # is this a named slide, or a new slide?
            if 'widgets' in s:
                target.add_and_show_slide(mode=mode, slide_name=slide, **s)
            else:
                target.show_slide(slide_name=slide, mode=mode, **s)

    def get_express_config(self, value):
        # express config for slides can either be a string (slide name) or a
        # list (widgets which are put on a new slide)

        if isinstance(value, list):
            return dict(widgets=value)
        else:
            return dict(slide=value)

    def validate_config(self, config):
        """Validates the slide_player: section of a config file (either a
        machine-wide config or a mode config).

        Args:
            config: A dict of the contents of the slide_player section
            from the config file. It's assumed that keys are event names, and
            values are settings for what the slide_player should do when that
            event is posted.

        Returns: A dict a validated entries.

        This method overrides the base method since the slide_player has
        unique options (including lists of widgets or single dict entries that
        are a widget settings instead of slide settings.

        """
        # first, we're looking to see if we have a string, a list, or a dict.
        # if it's a dict, we look to see whether we have a widgets: entry
        # or the name of some slide

        validated_config = dict()

        for event, settings in config.items():
            validated_config[event] = dict()
            validated_config[event]['slides'] = dict()

            if not isinstance(settings, dict):
                settings = {settings: dict()}

            for slide, slide_settings in settings.items():
                dict_is_widgets = False

                # if settings is list, it's widgets
                if isinstance(slide_settings, list):
                    slide_settings = dict(widgets=slide_settings)

                # Now check to see if all the settings are valid
                # slide settings. If not, assume it's a single widget settings.
                if isinstance(slide_settings, dict):
                    for key in slide_settings.keys():
                        if key not in ConfigValidator.config_spec['slide_player']:
                            dict_is_widgets = True
                            break

                    if dict_is_widgets:
                        slide_settings = dict(widgets=[slide_settings])

                    validated_config[event]['slides'].update(
                        self.validate_show_config(slide, slide_settings))

        return validated_config

    def validate_show_config(self, device, device_settings, serializable=True):
        validated_dict = super().validate_show_config(device, device_settings)

        # device is slide name

        for v in validated_dict.values():

            if 'transition' in v:
                if not isinstance(v['transition'], dict):
                    v['transition'] = dict(type=v['transition'])

                try:
                    v['transition'] = (
                        self.machine.config_validator.validate_config(
                            'transitions:{}'.format(
                                v['transition']['type']), v['transition']))

                except KeyError:
                    raise ValueError('transition: section of config requires a'
                                     ' "type:" setting')

            if 'widgets' in v:
                v['widgets'] = self.machine.widgets.process_config(
                    v['widgets'], serializable=serializable)

        return validated_dict

player_cls = MpfSlidePlayer
mc_player_cls = McSlidePlayer

def register_with_mpf(machine):
    return 'slide', MpfSlidePlayer(machine)
