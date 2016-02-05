
from kivy.logger import Logger
from mc.core.config_player import ConfigPlayer


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
                sound = self.mc.sounds[sound_name]
            except KeyError:
                Logger.warning("SoundPlayer: The specified sound does not exist ('{}') - "
                               "sound could not be played.".format(sound_name))
                return

            # Get track by name. If track was not provided, use the default track name from the sound.
            if s['track'] and s['track'] in self.mc.sound_system.tracks.keys():
                track = self.mc.sound_system.tracks[s['track']]
            else:
                track = sound.track

            track.play_sound(sound=sound, settings=s)

