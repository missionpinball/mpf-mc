from mpf.config_players.plugin_player import PluginPlayer


class MpfPlaylistPlayer(PluginPlayer):
    """Base class for part of the playlist player which runs as part of MPF.

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF, not the mpf-mc. MPF finds this instance because the mpf-mc setup.py
    has the following entry_point configured:

        playlist_player=mpfmc.config_players.playlist_player:register_with_mpf

    """
    config_file_section = 'playlist_player'
    show_section = 'playlists'


player_cls = MpfPlaylistPlayer


def register_with_mpf(machine):
    """Registers the playlist player plug-in with MPF"""
    return 'playlist', MpfPlaylistPlayer(machine)
