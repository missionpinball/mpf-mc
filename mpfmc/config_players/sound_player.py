"""Contains the sound config player class"""

from copy import deepcopy
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

    # pylint: disable=invalid-name
    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Plays a validated sounds: section from a sound_player: section of a
        config file or the sounds: section of a show.

        The config must be validated. Validated config looks like this:

        <sound_name>:
            <settings>: ...

        <settings> can be:

        action:
        priority:
        volume:
        loops:
        max_queue_time:

        Notes:
            Ducking settings and markers cannot currently be specified/overridden in the
            sound_player (they must be specified in the sounds section of a config file).

        """
        settings = deepcopy(settings)

        if 'sounds' in settings:
            settings = settings['sounds']

        for sound_name, s in settings.items():
            if self.check_delayed_play(sound_name, s, context, calling_context, priority, **kwargs):
                return

            try:
                s['priority'] += priority
            except (KeyError, TypeError):
                s['priority'] = priority

            # Retrieve sound asset by name
            try:
                sound = self.machine.sounds[sound_name]
            except KeyError:
                self.machine.log.error("SoundPlayer: The specified sound "
                                       "does not exist ('{}').".format(sound_name))
                return

            s.update(kwargs)

            action = s['action'].lower()
            del s['action']

            track = self.machine.sound_system.audio_interface.get_track_by_name(s.get('track') or sound.track)
            if track is None:
                self.machine.log.error("SoundPlayer: The specified track ('{}') "
                                       "does not exist. Unable to perform '{}' action "
                                       "on sound '{}'."
                                       .format(s['track'], action, sound_name))
                return

            # Determine action to perform
            if action == 'play':
                track.play_sound(sound, context, s)

            elif action == 'stop':
                if 'fade_out' in s:
                    track.stop_sound(sound, s['fade_out'])
                else:
                    track.stop_sound(sound)

            elif action == 'stop_looping':
                track.stop_sound_looping(sound)

            elif action == 'load':
                sound.load()

            elif action == 'unload':
                sound.unload()

            else:
                self.machine.log.error("SoundPlayer: The specified action "
                                       "is not valid ('{}').".format(action))

    def get_express_config(self, value):
        """ express config for sounds is simply a string (sound name)"""
        return dict(sound=value)

    # pylint: disable=too-many-branches
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

            if 'track' in settings:
                track = settings['track']

                if self.machine.sound_system.audio_interface.get_track_type(track) != "standard":
                    raise ValueError("SoundPlayer: An invalid audio track '{}' is specified for event '{}' "
                                     "(only standard audio tracks are supported).".format(track, event))

            for sound, sound_settings in settings.items():

                # Now check to see if all the settings are valid
                # sound settings. If not, assume it's a single sound settings.
                if isinstance(sound_settings, dict):
                    for key in sound_settings:
                        if key not in self.machine.config_validator.get_config_spec()['sound_player']:
                            break

                    validated_config[event]['sounds'].update(
                        self._validate_config_item(sound, sound_settings))

        return validated_config

    def clear_context(self, context):
        """Stop all sounds from this context."""
        self.machine.log.debug("SoundPlayer: Clearing context - applying mode_end_action for all active sounds")

        for index in range(self.machine.sound_system.audio_interface.get_track_count()):
            track = self.machine.sound_system.audio_interface.get_track(index)
            if track.type == "standard":
                track.clear_context(context)


McPlayerCls = McSoundPlayer
