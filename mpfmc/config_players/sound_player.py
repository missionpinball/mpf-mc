from mpf.config_players.plugin_player import PluginPlayer
from mpfmc.core.mc_config_player import McConfigPlayer


class MpfSoundPlayer(PluginPlayer):
    """

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF.

    """
    config_file_section = 'sound_player'



class McSoundPlayer(McConfigPlayer):
    pass

    # todo








player_cls = MpfSoundPlayer
mc_player_cls = McSoundPlayer

def register_with_mpf(machine):
    return 'sound', MpfSoundPlayer(machine)


