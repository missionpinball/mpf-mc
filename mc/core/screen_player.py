from mc.core.config_player import EventPlayer


class ScreenPlayer(EventPlayer):
    config_file_section = 'screen_player'

    def play(self, settings, mode=None):
        if mode and not mode.active:
            return

        self.mc.default_display.add_screen(settings['screen'],
                                           mode.config['screens'][
                                               settings['screen']])
