from mc.core.config_player import ConfigPlayer


class ScreenPlayer(ConfigPlayer):
    config_file_section = 'screen_player'

    def play(self, settings, mode=None):
        if mode and not mode.active:
            return

        print('PLAY', settings)

        # TODO change to central screen repo

        try:
            display = self.mc.displays[settings['display']]
        except KeyError:
            display = self.mc.default_display

        if mode:
            display.add_screen(settings['screen'],
                                               mode.config['screens'][
                                                   settings['screen']])
        else:
            display.add_screen(settings['screen'],
                                               self.mc.machine_config[
                                                   'screens'][settings['screen']])
