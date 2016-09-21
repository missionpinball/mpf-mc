"""Contains the sound config player class"""

# WARNING: Do not import kivy's logger here since that will trigger Kivy to
# load in the mpf process when MPF processes the MpfSoundPlayer
from copy import deepcopy

from mpf.config_players.plugin_player import PluginPlayer
from mpf.core.config_validator import ConfigValidator
from mpfmc.core.mc_config_player import McConfigPlayer


class McTrackPlayer(McConfigPlayer):
    """Base class for the Track Player that runs on the mpf-mc side of things.
    It receives all of its instructions via BCP from a MpfTrackPlayer instance
    running as part of MPF.

    The track_player: section of a config file (either the machine-wide or
    a mode-specific config) looks like this:

    track_player:
        <event_name>:
            <track_name>:
                <track_settings>: ...

    There is no express config for the track_player.

    To control the track settings (such as volume and action), enter the track name
    on the next line and the settings indented under it, like this:

    track_player:
        some_event:
            track_name:
                action: pause
                fade: 0.5 sec

Here are several various examples:

    track_player:
        some_event:
            music:
                action: set_volume
                volume: 0.65
                fade: 2 sec

        some_event2:
            sfx:
                action: stop
                fade: 0.75 sec

    """
    config_file_section = 'track_player'
    show_section = 'tracks'
    machine_collection_name = None

    # pylint: disable=invalid-name
    def play(self, settings, context, priority=0, **kwargs):
        """Initiates an action from a validated tracks: section from a track_player: section of a
        config file or the tracks: section of a show.

        The config must be validated. Validated config looks like this:

        <track_name>:
            <settings>: ...

        <settings> can be:

        action:
        volume:
        fade:
        """
        del priority
        instance_dict = self._get_instance_dict(context)
        settings = deepcopy(settings)

        if 'tracks' in settings:
            settings = settings['tracks']

        for track_name, s in settings.items():

            # Retrieve track by name
            try:
                sound = self.machine.tracks[track_name]
            except KeyError:
                self.machine.log.error("TrackPlayer: The specified track "
                                       "does not exist ('{}').".format(track_name))
                return

            s.update(kwargs)

            # Determine action to perform
            if s['action'].lower() == 'play':
                pass

            elif s['action'].lower() == 'stop':
                pass

            elif s['action'].lower() == 'pause':
                pass

            elif s['action'].lower() == 'resume':
                pass

            elif s['action'].lower() == 'set_volume':
                pass

            else:
                self.machine.log.error("TrackPlayer: The specified action "
                                       "is not valid ('{}').".format(s['action']))

    def get_express_config(self, value):
        """ express config for tracks is not supported"""
        del value
        raise AssertionError("Track Player does not support express config")

    # pylint: disable=too-many-branches
    def validate_config(self, config):
        """Validates the track_player: section of a config file (either a
        machine-wide config or a mode config).

        Args:
            config: A dict of the contents of the track_player section
            from the config file. It's assumed that keys are event names, and
            values are settings for what the track_player should do when that
            event is posted.

        Returns: A dict a validated entries.

        This method overrides the base method since the track_player has
        unique options.

        """
        # first, we're looking to see if we have a string, a list, or a dict.
        # if it's a dict, we look to see whether we have the name of some sound

        validated_config = dict()

        for event, settings in config.items():
            validated_config[event] = dict()
            validated_config[event]['tracks'] = dict()

            if not isinstance(settings, dict):
                settings = {settings: dict()}

            for track, track_settings in settings.items():

                # Now check to see if all the settings are valid
                # sound settings. If not, assume it's a single sound settings.
                if isinstance(track_settings, dict):
                    for key in track_settings.keys():
                        if key not in ConfigValidator.config_spec['track_player']:
                            break

                    validated_config[event]['tracks'].update(
                        self._validate_config_item(track, track_settings))

        return validated_config

    def _validate_config_item(self, device, device_settings):
        """Validates the config when in a show"""
        validated_dict = super()._validate_config_item(device, device_settings)
        # device is sound name
        return validated_dict

    def clear_context(self, context):
        """Because tracks are persistent for the life of the application, there is nothing
        to clear when the context ends."""
        del context

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
mc_player_cls = McTrackPlayer


def register_with_mpf(machine):
    """Registers the sound player plug-in with MPF"""
    return 'track', MpfTrackPlayer(machine)
