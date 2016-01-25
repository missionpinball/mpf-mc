
from kivy.logger import Logger
from mc.core.config_player import ConfigPlayer


class SoundPlayer(ConfigPlayer):
    config_file_section = 'sound_player'

    def additional_processing(self, config):
        return config

    def play(self, settings, mode=None):
        raise NotImplementedError

