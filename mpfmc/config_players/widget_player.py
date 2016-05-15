from copy import deepcopy

from mpf.config_players.plugin_player import PluginPlayer
from mpfmc.core.mc_config_player import McConfigPlayer


class MpfWidgetPlayer(PluginPlayer):
    """

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF.

    """
    config_file_section = 'widget_player'
    show_section = 'widgets'


class McWidgetPlayer(McConfigPlayer):
    """Base class for the Widget Player that runs on the mpf-mc side of things.
    It receives all of its instructions via BCP from an MpfWidgetPlayer
    instance
    running as part of MPF.
    """

    config_file_section = 'widget_player'
    show_section = 'widgets'
    machine_collection_name = 'widgets'

    def play(self, settings, key=None, priority=0, **kwargs):
        # **kwargs since this is an event callback
        del priority
        del kwargs

        settings = deepcopy(settings)

        if 'widgets' in settings:
            settings = settings['widgets']

        for widget, s in settings.items():
            s.pop('priority', None)
            slide = None
            action = s.pop('action')
            assert action in ('add', 'remove')

            if s['target']:
                try:
                    slide = self.machine.targets[s.pop('target')].current_slide
                except KeyError:  # pragma: no cover
                    pass

            if s['slide']:
                slide_name = s.pop('slide')
                try:
                    slide = self.machine.active_slides[slide_name]
                except KeyError:  # pragma: no cover
                    pass

            if action == 'remove':
                if s['key']:
                    key = s['key']
                else:
                    key = widget

                if slide:
                    slide.remove_widgets_by_key(key)
                else:
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

                continue

            if not slide:
                slide = self.machine.targets['default'].current_slide

            if not slide:  # pragma: no cover
                raise ValueError("Cannot add widget. No current slide")

            if action == 'add':

                if not s['key']:
                    try:
                        s['key'] = s['widget_settings'].pop('key')
                    except (KeyError, AttributeError):
                        s['key'] = key

                slide.add_widgets_from_library(name=widget, **s)

    def get_express_config(self, value):
        return dict(widget=value)

    def clear(self, key):
        self.remove_widgets(key)

    def remove_widgets(self, key):
        # remove widgets from slides
        for slide in self.machine.active_slides.values():
            slide.remove_widgets_by_key(key)

        # remove widgets from slide frame parents
        target_list = set(self.machine.targets.values())
        for target in target_list:
            for widget in [x for x in target.parent.children if
                           x.key == key]:
                target.parent.remove_widget(widget)


player_cls = MpfWidgetPlayer
mc_player_cls = McWidgetPlayer


def register_with_mpf(machine):
    return 'widget', MpfWidgetPlayer(machine)
