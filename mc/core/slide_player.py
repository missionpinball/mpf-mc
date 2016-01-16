from mc.core.config_player import ConfigPlayer


class SlidePlayer(ConfigPlayer):
    config_file_section = 'slide_player'

    def play(self, settings, mode=None):
        try:
            if not mode.active:
                return
        except AttributeError:
            pass

        if mode:
            priority = mode.priority
        else:
            priority = 0

        try:
            priority += settings['priority']
        except KeyError:
            pass

        try:
            target = self.mc.targets[settings['target']]
        except KeyError:
            if mode:
                target = mode.target
            else:
                target = self.mc.targets['default']

        if mode:
            target.add_slide(name=settings['slide'],
                             config=mode.config['slides'][settings['slide']])
        else:
            target.add_slide(name=settings['slide'],
                             config=self.mc.machine_config['slides'][settings[
                                 'slide']])
