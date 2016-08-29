"""Widget player which can add and remove widgets from slides."""
from copy import deepcopy

from mpf.config_players.plugin_player import PluginPlayer
from mpf.core.events import EventHandlerKey

from mpfmc.core.mc_config_player import McConfigPlayer


class MpfWidgetPlayer(PluginPlayer):

    """Widget Player in MPF.

    Note: This class is loaded by MPF and everything in it is in the context of MPF.
    """

    config_file_section = 'widget_player'
    show_section = 'widgets'


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
    machine_collection_name = 'widgets'

    def _get_slide(self, s):
        slide = None
        if s['target']:
            try:
                slide = self.machine.targets[s['target']].current_slide
                # need to del here instead of pop so it still exists for
                # the exception
                del s['target']
            except KeyError:
                raise KeyError(
                    "Cannot add widget to target '{}' as that is not a "
                    "valid display target".format(s['target']))

        if s['slide']:
            slide_name = s.pop('slide')
            try:
                slide = self.machine.active_slides[slide_name]
            except KeyError:
                # check if slide does exist
                if slide_name not in self.machine.slides:
                    raise KeyError(
                        "Cannot add widget to slide '{}' as that is not a "
                        "valid slide".format(slide_name))
                else:
                    raise SlideNotActiveError(slide_name=slide_name)

        return slide

    def _action_add(self, s, instance_dict, widget, context):
        try:
            slide = self._get_slide(s)
        except SlideNotActiveError as e:
            handler = self.machine.events.add_handler(
                "slide_{}_active".format(e.slide_name), self._add_widget_to_slide_when_active,
                slide_name=e.slide_name, widget=widget, s=s, context=context)
            instance_dict[s['key']] = handler
            return

        if not slide:
            slide = self.machine.targets['default'].current_slide

        if not slide:  # pragma: no cover
            raise ValueError("Cannot add widget. No current slide")

        if not s['key']:
            try:
                s['key'] = s['widget_settings'].pop('key')
            except (KeyError, AttributeError):
                s['key'] = context + "-" + widget

        widgets = slide.add_widgets_from_library(name=widget, **s)
        instance_dict[s['key']] = (slide, widgets)

    def _action_remove(self, s, instance_dict, widget, context):
        try:
            slide = self._get_slide(s)
        except SlideNotActiveError:
            slide = None

        if s['key']:
            key = s['key']
        else:
            key = context + "-" + widget

        if key in instance_dict and isinstance(instance_dict[key], EventHandlerKey):
            self.machine.events.remove_handler_by_key(instance_dict[key])

        if slide:
            slide.remove_widgets_by_key(key)
        else:
            self._remove_widget_by_key(key)

        if key in instance_dict:
            del instance_dict[key]

    def play(self, settings, context, priority=0, **kwargs):
        """Play widgets."""
        # **kwargs since this is an event callback
        del priority
        del kwargs
        settings = deepcopy(settings)
        instance_dict = self._get_instance_dict(context)

        if 'widgets' in settings:
            settings = settings['widgets']

        for widget, s in settings.items():
            s.pop('priority', None)
            action = s.pop('action')
            assert action in ('add', 'remove', 'update')

            if action == "add":
                self._action_add(s, instance_dict, widget, context)
            elif action == "remove":
                self._action_remove(s, instance_dict, widget, context)
            elif action == "update":
                self._action_remove(s, instance_dict, widget, context)
                self._action_add(s, instance_dict, widget, context)
            else:
                raise AssertionError("Invalid action {} in {}".format(action, widget))

    def _remove_widget_by_key(self, key):
        """Remove widget by key."""
        for target in self.machine.targets.values():
            for w in target.slide_frame_parent.walk():
                try:
                    if w.key == key:
                        w.parent.remove_widget(w)
                except AttributeError:
                    pass
            for x in target.screens:
                for y in x.walk():
                    try:
                        if y.key == key:
                            x.remove_widget(y)
                    except AttributeError:
                        pass

    def _add_widget_to_slide_when_active(self, slide_name, widget, s, context, **kwargs):
        del kwargs
        instance_dict = self._get_instance_dict(context)
        slide = self.machine.active_slides[slide_name]
        widgets = slide.add_widgets_from_library(name=widget, **s)
        if s['key'] in instance_dict and isinstance(instance_dict[s['key']], EventHandlerKey):
            self.machine.events.remove_handler_by_key(instance_dict[s['key']])
        instance_dict[s['key']] = (slide, widgets)

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

player_cls = MpfWidgetPlayer
mc_player_cls = McWidgetPlayer


def register_with_mpf(machine):
    """Register widget player in MPF module."""
    return 'widget', MpfWidgetPlayer(machine)
