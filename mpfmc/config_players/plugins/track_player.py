from mpf.config_players.plugin_player import PluginPlayer


class MpfTrackPlayer(PluginPlayer):
    """Base class for part of the track player which runs as part of MPF.

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF, not the mpf-mc. MPF finds this instance because the mpf-mc setup.py
    has the following entry_point configured:

        track_player=mpfmc.config_players.track_player:register_with_mpf

    """
    config_file_section = 'track_player'
    show_section = 'tracks'


player_cls = MpfTrackPlayer


def register_with_mpf(machine):
    """Registers the sound player plug-in with MPF"""
    return 'track', MpfTrackPlayer(machine)
