from mc.core.config_player import ConfigPlayer
from mc.uix.slide import Slide

class WidgetPlayer(ConfigPlayer):
    config_file_section = 'widget_player'

    def play(self, settings, mode=None):
        if mode and not mode.active:
            return

        # figure out the target slide. If there is a slide, it will win
        slide = None

        if settings['target']:
            try:
                slide = self.mc.targets[settings['target']].current_slide
            except KeyError:
                pass

        if settings['slide']:
            try:
                slide = Slide.active_slides[settings['slide']]
            except KeyError:
                pass

        if not slide:
            slide = self.mc.targets['default'].current_slide

        if not slide:
            return

        for widget in settings['widget']:
            slide.add_widgets_from_library(name=widget, mode=mode)

