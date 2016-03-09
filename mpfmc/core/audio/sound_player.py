
from kivy.logger import Logger
from mpf.core.config_player import ConfigPlayer


# todo move / remove this module

class SoundPlayer(ConfigPlayer):
    config_file_section = 'sound_player'

    def additional_processing(self, config):
        return config

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

