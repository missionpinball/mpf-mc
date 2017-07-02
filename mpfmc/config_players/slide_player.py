from copy import deepcopy
from mpf.core.config_validator import ConfigValidator
from mpf.core.events import EventHandlerKey
from mpfmc.core.mc_config_player import McConfigPlayer


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

    def _add_slide_to_target_when_active(self, target_name, key, slide_name, s,
                                         instance_dict, **kwargs):
        del kwargs
        target = self.machine.targets[target_name]
        if 'widgets' in s:
            target.add_and_show_slide(key=key, slide_name=slide_name, **s)
        else:
            target.show_slide(slide_name=slide_name, key=key, **s)

        if slide_name not in instance_dict[target_name]:
            instance_dict[target_name][slide_name] = False

    def _delayed_actions(self, target_name, s, slide, instance_dict,
                         full_context):
        if target_name not in instance_dict:
            instance_dict[target_name] = {}
        if (slide in instance_dict[target_name] and
                instance_dict[target_name][slide]):
            self.machine.events.remove_handler_by_key(
                instance_dict[target_name][slide])
        if s['action'] == "play":
            handler = self.machine.events.add_handler(
                "display_{}_ready".format(target_name),
                self._add_slide_to_target_when_active,
                key=full_context, slide_name=slide, s=s,
                target_name=target_name, instance_dict=instance_dict)
            instance_dict[target_name][slide] = handler

    def play(self, settings, context, priority=0, **kwargs):
        instance_dict = self._get_instance_dict(context)
        full_context = self._get_full_context(context)
        settings = deepcopy(settings)

        if 'slides' in settings:
            settings = settings['slides']

        for slide, s in settings.items():
            s.update(kwargs)

            if s["slide"]:
                slide = s['slide']

            try:
                s['priority'] += priority
            except (KeyError, TypeError):
                s['priority'] = priority

            if s['target']:
                target_name = s['target']
                try:
                    target = self.machine.targets[target_name]
                except KeyError:
                    # target does not exist yet. perform action when it appears
                    self._delayed_actions(target_name, s, slide, instance_dict,
                                          full_context)
                    return
            else:
                target = self.machine.targets['default']
                target_name = "default"

            self._delayed_actions(target_name, s, slide, instance_dict,
                                  full_context)

            # remove target
            s.pop("target")

            if s['action'] == 'play':
                # is this a named slide, or a new slide?
                if 'widgets' in s:
                    target.add_and_show_slide(key=full_context,
                                              slide_name=slide, **s)
                else:
                    target.show_slide(slide_name=slide, key=full_context, **s)

                target.get_screen(slide).on_slide_play()

                if slide not in instance_dict[target_name]:
                    instance_dict[target_name][slide] = False

            elif s['action'] == 'remove':
                if slide in instance_dict[target_name]:
                    del instance_dict[target_name][slide]
                    target.remove_slide(slide=slide,
                                        transition_config=s['transition'])

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

            if isinstance(settings, list):
                raise AssertionError(
                    "Config of slide_player for event {} is broken. "
                    "It expects a dict not a list".format(event))

            if not isinstance(settings, dict):
                settings = {settings: dict()}

            for slide, slide_settings in settings.items():
                dict_is_widgets = False

                # if settings is list, it's widgets
                if isinstance(slide_settings, list):
                    # convert it to a dict by moving this list of settings into
                    # a dict key called "widgets"
                    slide_settings = dict(widgets=slide_settings)

                # Now we have a dict, but is this a dict of settings for a
                # single slide, or a dict of settings for the slide player
                # itself?

                # So let's check the keys and see if they're all valid keys
                # for a slide_player. If so, it's slide_player keys. If not,
                # we assume they're widgets for a slide.

                elif isinstance(slide_settings, str):
                    # slide_settings could be a string 'slide: slide_name',
                    # so we rename the key to the slide name with an empty dict
                    slide = slide_settings
                    slide_settings = dict()

                elif not isinstance(slide_settings, dict):
                    raise AssertionError(
                        "Expected a dict in slide_player {}:{}.".format(event,
                                                                        slide))

                for key in slide_settings.keys():
                    if key not in ConfigValidator.config_spec['slide_player']:
                        dict_is_widgets = True
                        break

                if dict_is_widgets:
                    slide_settings = dict(widgets=[slide_settings])

                validated_config[event]['slides'].update(
                    self._validate_config_item(slide, slide_settings))

        return validated_config

    def _validate_config_item(self, device, device_settings):
        validated_dict = super()._validate_config_item(device, device_settings)

        # device is slide name

        for v in validated_dict.values():
            if 'widgets' in v:
                v['widgets'] = self.machine.widgets.process_config(
                    v['widgets'])

            self.machine.transition_manager.validate_transitions(v)

        return validated_dict

    def clear_context(self, context):
        """Remove all slides from this player context."""
        instance_dict = self._get_instance_dict(context)
        for target_name, slides in instance_dict.items():
            try:
                target = self.machine.targets[target_name]
            except KeyError:
                continue
            for slide, handler in slides.items():
                if isinstance(handler, EventHandlerKey):
                    self.machine.events.remove_handler_by_key(handler)
                target.remove_slide(slide)

        self._reset_instance_dict(context)


mc_player_cls = McSlidePlayer
