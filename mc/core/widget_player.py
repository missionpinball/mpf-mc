from mc.core.config_player import ConfigPlayer
from mc.uix.slide import Slide

class WidgetPlayer(ConfigPlayer):
    config_file_section = 'widget_player'

    def play(self, settings, mode=None):
        if mode and not mode.active:
            return

        for s in settings:

            # figure out the target slide. If there is a slide, it will win
            slide = None

            if s['target']:
                try:
                    slide = self.mc.targets[s['target']].current_slide
                except KeyError:
                    pass

            if s['slide']:
                try:
                    slide = self.mc.active_slides[s['slide']]
                except KeyError:
                    pass

            if not slide:
                slide = self.mc.targets['default'].current_slide

            if not slide:
                return

            for widget in s['widget']:
                slide.add_widgets_from_library(name=widget, mode=mode)

