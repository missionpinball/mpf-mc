from mpf.config_players.plugin_player import PluginPlayer
from mpfmc.core.mc_config_player import McConfigPlayer


class MpfWidgetPlayer(PluginPlayer):
    """

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF.

    """
    config_file_section = 'widget_player'

    def play(self, settings, mode=None, play_kwargs=None, **kwargs):

        if not play_kwargs:
            play_kwargs = kwargs
        else:
            play_kwargs.update(kwargs)

        super().play(settings, mode, play_kwargs)


class McWidgetPlayer(McConfigPlayer):
    """Base class for the Widget Player that runs on the mpf-mc side of things.
    It receives all of its instructions via BCP from an MpfWidgetPlayer
    instance
    running as part of MPF.
    """

    config_file_section = 'widget_player'
    show_section = 'widgets'
    machine_collection_name = 'widgets'

    def play(self, settings, mode=None, caller=None, play_kwargs=None,
             **kwargs):

        # todo add play_kwargs and kwargs, use McSlidePlayer as example

        super().play(settings, mode, caller, play_kwargs)

        if 'widgets' in settings:
            settings = settings['widgets']

        for widget, s in settings.items():

            slide = None

            if s['target']:
                try:
                    slide = self.machine.targets[s['target']].current_slide
                except KeyError:  # pragma: no cover
                    pass

            if s['slide']:
                try:
                    slide = self.machine.active_slides[s['slide']]
                except KeyError:  # pragma: no cover
                    pass

            if not slide:
                slide = self.machine.targets['default'].current_slide

            if not slide:
                continue  # pragma: no cover

            slide.add_widgets_from_library(name=widget, mode=mode)


    def get_express_config(self, value):
        return dict(widget=value)


player_cls = MpfWidgetPlayer
mc_player_cls = McWidgetPlayer

def register_with_mpf(machine):
    return 'widget', MpfWidgetPlayer(machine)
