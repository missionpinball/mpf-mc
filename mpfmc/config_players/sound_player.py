from mpf.core.config_player import ConfigPlayer


class SoundPlayer(ConfigPlayer):
    """

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF.

    """
    config_file_section = 'sound_player'


player_cls = SoundPlayer

def register_with_mpf(machine):
    return 'sound', SoundPlayer(machine)