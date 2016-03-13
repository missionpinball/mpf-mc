from mpf.config_players.plugin_player import PluginPlayer
from mpfmc.core.mc_config_player import McConfigPlayer


class McSoundPlayer(McConfigPlayer):

    def get_express_config(self, value):
        return dict(sound=value)

    def play(self, settings, mode=None, caller=None, priority=None,
             play_kwargs=None, **kwargs):
        super().play(settings, mode, caller, priority, play_kwargs)

        if mode and not mode.active:
            return

        for s in settings:  # settings is a list of one or more sound configs

            # Retrieve sound asset by name
            sound_name = s['sound']
            try:
                sound = self.machine.sounds[sound_name]
            except KeyError:
                Logger.warning("SoundPlayer: The specified sound does not exist ('{}') - "
                               "sound could not be played.".format(sound_name))
                return

            # Make a copy of the settings since we need to remove the 'sound' entry
            # before playing the sound.
            config = s.copy()
            del config['sound']

            # Get track by name. If track was not provided, use the default track name from the sound.
            if config['track'] and config['track'] in self.mc.sound_system.tracks.keys():
                track = self.machine.sound_system.tracks[config['track']]
            else:
                track = sound.track

            track.play_sound(sound=sound, **config)


class MpfSoundPlayer(PluginPlayer):
    """

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF.

    """
    config_file_section = 'sound_player'












player_cls = MpfSoundPlayer
mc_player_cls = McSoundPlayer

def register_with_mpf(machine):
    return 'sound', MpfSoundPlayer(machine)


