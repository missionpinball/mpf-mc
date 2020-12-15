from copy import deepcopy
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
    machine_collection_name = None  # slides are not real devices currently

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Process a slide_player event."""
        instance_dict = self._get_instance_dict(context)
        full_context = self._get_full_context(context)

        self.machine.log.info("SlidePlayer: Play called with settings=%s", settings)

        settings = settings.get('slides', settings)

        for slide, s in settings.items():
            if not isinstance(slide, str):
                if slide.condition and not slide.condition.evaluate(kwargs):
                    continue
                slide = slide.name

            s = deepcopy(s)
            s.update(kwargs)

            if s.get("slide"):
                slide = s['slide']
            elif slide == "widgets":
                # name of anonymous slides depends on context + event name
                slide = "{}-{}".format(full_context, calling_context)

            try:
                s['priority'] += priority
            except (KeyError, TypeError):
                s['priority'] = priority

            target_name, target = self._get_target(s)
            # Target has been disabled via config setting, ignore all slides for it
            if not target.enabled:
                return

            # remove target
            s.pop("target")

            if target_name not in instance_dict:
                instance_dict[target_name] = {}

            if s['action'] == 'play':
                # remove slide if it already exists
                if slide in instance_dict[target_name]:
                    instance_dict[target_name][slide].remove()
                    del instance_dict[target_name][slide]

                # is this a named slide, or a new slide?
                self.machine.log.debug("SlidePlayer: Playing slide '%s' on target '%s' (Args=%s)",
                                       slide,
                                       target.name,
                                       s)
                if 'widgets' in s:
                    target.add_and_show_slide(key=full_context,
                                              slide_name=slide, play_kwargs=s['tokens'], **s)
                else:
                    target.show_slide(slide_name=slide, key=full_context, play_kwargs=s['tokens'], **s)

                target.get_screen(slide).on_slide_play()

                instance_dict[target_name][slide] = target.get_slide(slide)

            elif s['action'] == 'remove' and slide in instance_dict[target_name]:
                del instance_dict[target_name][slide]
                target.remove_slide(slide=slide,
                                    transition_config=s['transition'] if 'transition' in s else [])

    def _expand_device(self, device):
        # parse conditionals
        devices = super()._expand_device(device)
        for index, device_entry in enumerate(devices):
            if isinstance(device_entry, str):
                devices[index] = self.machine.placeholder_manager.parse_conditional_template(device_entry)
        return devices

    def _get_target(self, settings):
        if settings['target']:
            target_name = settings['target']
        else:
            target_name = 'default'

        if target_name not in self.machine.targets or not self.machine.targets[target_name].ready:
            # Target does not exist yet or is not ready. Perform action when it is ready
            raise AssertionError("Target {} not ready".format(target_name))

        return target_name, self.machine.targets[target_name]

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
                    if slide_settings == "remove":
                        slide_settings = {"action": "remove"}
                    else:
                        slide = slide_settings
                        slide_settings = dict()

                elif not isinstance(slide_settings, dict):
                    raise AssertionError(
                        "Expected a dict in slide_player {}:{}.".format(event,
                                                                        slide))

                for key in slide_settings:
                    if key not in self.machine.config_validator.get_config_spec()['slide_player']:
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
        for config in validated_dict.values():
            if config['target'] and config['target'] not in self.machine.targets:
                raise AssertionError("Target {} does not exist.".format(config['target']))
            if 'widgets' in config:
                # verify widgets
                config['widgets'] = self.machine.widgets.process_config(
                    config['widgets'])
            else:
                # verify that slide exists
                if config['slide']:
                    slide = config['slide']
                else:
                    slide = self.machine.placeholder_manager.parse_conditional_template(device).name

                if config['action'] == "play" and slide not in self.machine.slides:
                    raise AssertionError("Slide {} not found".format(slide))

            self.machine.transition_manager.validate_transitions(config)

        return validated_dict

    def clear_context(self, context):
        """Remove all slides from this player context."""
        instance_dict = self._get_instance_dict(context)
        for _, slides in instance_dict.items():
            for slide in slides.values():
                slide.remove()

        self._reset_instance_dict(context)


McPlayerCls = McSlidePlayer
