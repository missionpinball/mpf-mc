from mpf.core.config_player import ConfigPlayer

class WidgetPlayer(ConfigPlayer):
    """

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF.

    """
    config_file_section = 'widget_player'

    def play(self, settings, mode=None, **kwargs):
        super().play(settings, mode, **kwargs)

        for s in settings:  # settings is a list of widget configs

            # figure out the target slide. If there is a slide, it will win
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
                return  # pragma: no cover

            for widget in s['widget']:
                slide.add_widgets_from_library(name=widget, mode=mode,
                                               **kwargs)

player_cls = WidgetPlayer

def register_with_mpf(machine):
    return 'widget', WidgetPlayer(machine)