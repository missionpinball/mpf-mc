from mpf.config_players.plugin_player import PluginPlayer


class MpfSoundLoopPlayer(PluginPlayer):
    """Base class for part of the sound loop player which runs as part of MPF.

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF, not the mpf-mc. MPF finds this instance because the mpf-mc setup.py
    has the following entry_point configured:

        sound_loop_player=mpfmc.config_players.sound_loop_player:register_with_mpf

    """
    config_file_section = 'sound_loop_player'
    show_section = 'sound_loop_sets'


player_cls = MpfSoundLoopPlayer


def register_with_mpf(machine):
    """Registers the sound loop player plug-in with MPF"""
    return 'sound_loop', MpfSoundLoopPlayer(machine)
