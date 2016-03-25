from copy import deepcopy

from mpf.config_players.plugin_player import PluginPlayer
from mpf.core.config_validator import ConfigValidator
from mpfmc.core.mc_config_player import McConfigPlayer

class McSoundPlayer(McConfigPlayer):
    """Base class for the Sound Player that runs on the mpf-mc side of things.
    It receives all of its instructions via BCP from a MpfSoundPlayer instance
    running as part of MPF.

    The sound_player: section of a config file (either the machine-wide or
    a mode-specific config) looks like this:

    sound_player:
        <event_name>:
            <sound_name>:
                <sound_settings>: ...

    The express config just puts a sound_name next to an event.

    sound_player:
        some_event: sound_name_to_play

    If you want to control other settings (such as track, priority, volume,
    loops, etc.), enter the sound name on the next line and the settings
    indented under it, like this:

    sound_player:
        some_event:
            sound_name_to_play:
                volume: 0.35
                max_queue_time: 1 sec

Here are several various examples:

    sound_player:
        some_event:
            sound1:
                volume: 0.65

        some_event2:
            sound2:
                volume: -4.5 db
                priority: 100
                max_queue_time: 500 ms

        some_event3: sound3

    """
    config_file_section = 'sound_player'
    show_section = 'sounds'
    machine_collection_name = 'sounds'

    def play(self, settings, mode=None, caller=None,
             priority=0, play_kwargs=None, **kwargs):
        """Plays a validated sounds: section from a sound_player: section of a
        config file or the sounds: section of a show.

        The config must be validated. Validated config looks like this:

        <sound_name>:
            <settings>: ...

        <settings> can be:

        priority:
        track:
        volume:
        loops:
        max_queue_time:

        Notes:
            Ducking settings cannot currently be specified in the sound_player (they
            must be specified in the sounds section of a config file.

        """
        # super().play(settings, mode, caller, priority, play_kwargs)

        # todo figure out where the settings are coming from and see if we can
        # move the deepcopy there?
        settings = deepcopy(settings)

        if 'play_kwargs' in settings:
            play_kwargs = settings.pop('play_kwargs')

        if 'sounds' in settings:
            settings = settings['sounds']

        for sound_name, s in settings.items():

            try:
                s['priority'] += priority
            except (KeyError, TypeError):
                s['priority'] = priority

            # figure out track first since we need that to play a sound

            # Retrieve sound asset by name
            try:
                sound = self.machine.sounds[sound_name]
            except KeyError:
                Logger.warning("SoundPlayer: The specified sound does not exist ('{}') - "
                               "sound could not be played.".format(sound_name))
                return

            if play_kwargs:
                s.update(play_kwargs)

            s.update(kwargs)

            # Get track by name. If track was not provided, use the default track name from the sound.
            try:
                track = self.machine.sound_system.tracks[s.pop('track')]
            except KeyError:
                track = sound.track

            track.play_sound(sound=sound, **s)

    def get_express_config(self, value):
        # express config for sounds is simply a string (sound name)
        return dict(sound=value)

    def validate_config(self, config):
        """Validates the sound_player: section of a config file (either a
        machine-wide config or a mode config).

        Args:
            config: A dict of the contents of the sound_player section
            from the config file. It's assumed that keys are event names, and
            values are settings for what the sound_player should do when that
            event is posted.

        Returns: A dict a validated entries.

        This method overrides the base method since the sound_player has
        unique options.

        """
        # first, we're looking to see if we have a string, a list, or a dict.
        # if it's a dict, we look to see whether we have the name of some sound

        validated_config = dict()

        for event, settings in config.items():
            validated_config[event] = dict()
            validated_config[event]['sounds'] = dict()

            if not isinstance(settings, dict):
                settings = {settings: dict()}

            for sound, sound_settings in settings.items():

                # Now check to see if all the settings are valid
                # sound settings. If not, assume it's a single sound settings.
                if isinstance(sound_settings, dict):
                    for key in sound_settings.keys():
                        if key not in ConfigValidator.config_spec['sound_player']:
                            break

                    validated_config[event]['sounds'].update(
                        self.validate_show_config(sound, sound_settings))

        return validated_config

    def validate_show_config(self, device, device_settings, serializable=True):
        del serializable
        validated_dict = super().validate_show_config(device, device_settings)
        # device is sound name
        return validated_dict


class MpfSoundPlayer(PluginPlayer):
    """Base class for part of the sound player which runs as part of MPF.

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF, not the mpf-mc. MPF finds this instance because the mpf-mc setup.py
    has the following entry_point configured:

        sound_player=mpfmc.config_players.sound_player:register_with_mpf

    """
    config_file_section = 'sound_player'
    show_section = 'sounds'

    def validate_show_config(self, device, device_settings, serializable=True):
        # device is sound name, device_settings

        device_settings = self.machine.config_validator.validate_config("sound_player", device_settings)

        return_dict = dict()
        return_dict[device] = device_settings

        return return_dict


player_cls = MpfSoundPlayer
mc_player_cls = McSoundPlayer


def register_with_mpf(machine):
    return 'sound', MpfSoundPlayer(machine)
