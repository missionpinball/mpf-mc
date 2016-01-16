from mc.core.config_player import ConfigPlayer


class SlidePlayer(ConfigPlayer):
    config_file_section = 'slide_player'

    def play(self, settings, mode=None):
        if mode and not mode.active:
            return

        try:
            display = self.mc.displays[settings['display']]
        except KeyError:
            display = self.mc.default_display

        if mode:
            display.add_slide(name=settings['slide'],
                               config=mode.config['slides'][
                                   settings['slide']])
        else:
            display.add_slide(name=settings['slide'],
                               config=self.mc.machine_config[
                                   'slides'][settings['slide']])
