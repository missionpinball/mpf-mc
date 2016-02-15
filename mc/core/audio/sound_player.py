
from kivy.logger import Logger
from mpf.core.config_player import ConfigPlayer


class SoundPlayer(ConfigPlayer):
    config_file_section = 'sound_player'

    def additional_processing(self, config):
        return config

    def play(self, settings, mode=None, **kwargs):
        try:
            if not mode.active:
                return
        except AttributeError:
            pass

        for s in settings:  # settings is a list of one or more sound configs

            # Retrieve sound asset by name
            sound_name = s['sound']
            try:
                sound = self.machine.sounds[sound_name]
            except KeyError:
                Logger.warning("SoundPlayer: The specified sound does not exist ('{}') - "
                               "sound could not be played.".format(sound_name))
                return

            config = s.copy()
            del config['sound']

            # Get track by name. If track was not provided, use the default track name from the sound.
            if config['track'] and config['track'] in self.mc.sound_system.tracks.keys():
                track = self.machine.sound_system.tracks[config['track']]
            else:
                track = sound.track

            track.play_sound(sound=sound, **config)

