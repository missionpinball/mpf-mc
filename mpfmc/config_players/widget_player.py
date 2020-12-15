"""Widget player which can add and remove widgets from slides."""

from copy import deepcopy
from mpf.core.events import EventHandlerKey
from mpfmc.core.mc_config_player import McConfigPlayer
from mpfmc.uix.widget import create_widget_objects_from_library


class SlideNotActiveError(Exception):

    """Slide is not currently active but exists."""

    def __init__(self, slide_name, *args, **kwargs):
        self.slide_name = slide_name
        super().__init__(*args, **kwargs)


class McWidgetPlayer(McConfigPlayer):

    """Base class for the Widget Player that runs on the mpf-mc side of things.

    It receives all of its instructions via BCP from an MpfWidgetPlayer
    instance running as part of MPF.
    """

    config_file_section = 'widget_player'
    show_section = 'widgets'
    machine_collection_name = None  # widgets are not real devices currently

    def _get_slide(self, s):
        slide = None
        if s.get('slide'):
            slide_name = s['slide']
            try:
                slide = self.machine.active_slides[slide_name]
            except KeyError:
                # check if slide does exist
                if slide_name not in self.machine.slides:
                    raise KeyError(
                        "Widget Player Error: Slide name '{}' is not valid "
                        "slide. Widget config that caused this: "
                        "{}".format(slide_name, s))

                raise SlideNotActiveError(slide_name=slide_name)

        return slide

    # pylint: disable-msg=too-many-arguments
    def _action_add(self, s, instance_dict, widget, context, play_kwargs):
        if not s['key']:
            try:
                s['key'] = s['widget_settings'].pop('key')
            except (KeyError, AttributeError):
                s['key'] = context + "-" + widget

        if s.get('target'):

            try:
                target = self.machine.targets[s['target']]

            except KeyError:
                raise KeyError("Widget player invalid target '{}'. Current "
                               "valid targets: {} Settings: "
                               "{} Widget: {} Context: {} Play kwargs: {}".
                               format(self.machine.targets, s['target'], s,
                                      widget, context, play_kwargs))

            # remove any instances of this widget from this slide first
            target.remove_widgets_by_key(s['key'])

            target.add_widgets_to_current_slide(
                create_widget_objects_from_library(mc=self.machine,
                                                   name=widget,
                                                   play_kwargs=play_kwargs,
                                                   **s))  # todo
            if not s['key'] in instance_dict:
                instance_dict[s['key']] = True

            return

        priority = s.pop("priority", 1)

        if 'slide' in s and s['slide']:
            if s['key'] in instance_dict and isinstance(instance_dict[s['key']], EventHandlerKey):
                self.machine.events.remove_handler_by_key(instance_dict[s['key']])
            handler = self.machine.events.add_handler(
                "slide_{}_created".format(s['slide']), self._add_widget_to_slide_when_active,
                slide_name=s['slide'], widget=widget, s=s, priority=priority, play_kwargs=play_kwargs)
            instance_dict[s['key']] = handler

        try:
            slide = self._get_slide(s)
        except SlideNotActiveError:
            return

        if not slide:
            slide = self.machine.targets['default'].current_slide

        if not slide:  # pragma: no cover
            raise ValueError("Cannot add widget. No current slide")

        # remove from any slides since we are not targeting a specific slide
        self._remove_widget_by_key(s['key'])
        # add widget
        slide.add_widgets_from_library(name=widget, play_kwargs=play_kwargs, **s)
        if not s['key'] in instance_dict:
            instance_dict[s['key']] = True

    def _validate_config_item(self, device, device_settings):
        validated_dict = super()._validate_config_item(device, device_settings)
        for widget, widget_settings in validated_dict.items():
            if widget_settings['action'] == "add" and widget not in self.machine.widgets:
                raise AssertionError("Unknown widget {}".format(widget))
            if widget_settings["target"] and widget_settings["target"] not in self.machine.targets:
                raise AssertionError("Unknown target {}".format(widget_settings["target"]))

        return validated_dict

    def _action_remove(self, s, instance_dict, widget, context):
        if s['key']:
            key = s['key']
        else:
            key = context + "-" + widget

        if key in instance_dict and isinstance(instance_dict[key], EventHandlerKey):
            self.machine.events.remove_handler_by_key(instance_dict[key])

        if key in instance_dict:
            del instance_dict[key]

        try:
            slide = self._get_slide(s)
        except SlideNotActiveError:
            return

        if slide:
            slide.remove_widgets_by_key(key)
        else:
            self._remove_widget_by_key(key)

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Play widgets."""
        # **kwargs since this is an event callback
        del priority
        del calling_context
        settings = deepcopy(settings)
        instance_dict = self._get_instance_dict(context)

        if 'widgets' in settings:
            settings = settings['widgets']

        for widget, s in settings.items():
            action = s.pop('action')
            assert action in ('add', 'remove', 'update')

            if action == "add":
                self._action_add(s, instance_dict, widget, context, kwargs)
            elif action == "remove":
                self._action_remove(s, instance_dict, widget, context)
            elif action == "update":
                self._action_remove(s, instance_dict, widget, context)
                self._action_add(s, instance_dict, widget, context, kwargs)
            else:
                raise AssertionError("Invalid action {} in {}".format(action, widget))

    def _remove_widget_by_key(self, key):
        """Remove widget by key."""
        for target in self.machine.targets.values():
            target.remove_widgets_by_key(key)

    def _add_widget_to_slide_when_active(self, slide_name, widget, s, play_kwargs, **kwargs):
        del kwargs
        if slide_name in self.machine.active_slides:
            slide = self.machine.active_slides[slide_name]
            # remove any instances of this widget from this slide first
            slide.remove_widgets_by_key(s['key'])
            # add widget
            slide.add_widgets_from_library(name=widget, play_kwargs=play_kwargs, **s)

    def get_express_config(self, value):
        """Parse express config."""
        return dict(widget=value)

    def clear_context(self, context):
        """Clear context."""
        instance_dict = self._get_instance_dict(context)
        for key in instance_dict:
            if isinstance(instance_dict[key], EventHandlerKey):
                self.machine.events.remove_handler_by_key(instance_dict[key])

            self._remove_widget_by_key(key)

        self._reset_instance_dict(context)


McPlayerCls = McWidgetPlayer
