"""Contains the sound config player class."""
# WARNING: Do not import kivy's logger here since that will trigger Kivy to
# load in the mpf process when MPF processes the MpfSoundPlayer
from copy import deepcopy

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
    def play(self, settings, context, calling_context, priority=0, **kwargs):
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
        del calling_context
        settings = deepcopy(settings)

        if 'tracks' in settings:
            settings = settings['tracks']

        for track_name, s in settings.items():

            selected_tracks = dict()

            # Track name '__all__' indicates the action should be performed on all tracks
            if track_name == "__all__":
                selected_tracks = self.machine.sound_system.tracks
            else:
                # Single track name specified - retrieve track by name
                try:
                    selected_track = self.machine.sound_system.tracks[track_name]
                    selected_tracks[selected_track.name] = selected_track
                except KeyError:
                    self.machine.log.error("TrackPlayer: The specified audio track "
                                           "does not exist ('{}').".format(track_name))
                    return

            s.update(kwargs)

            # TODO: perform validation on parameters

            # Loop over selected tracks performing action with settings on each one
            for track in selected_tracks.values():

                # Determine action to perform
                if s['action'].lower() == 'play':
                    track.play(s['fade'])

                elif s['action'].lower() == 'stop':
                    track.stop(s['fade'])

                elif s['action'].lower() == 'pause':
                    track.pause(s['fade'])

                elif s['action'].lower() == 'set_volume':
                    track.set_volume(s['volume'], s['fade'])

                elif s['action'].lower() == 'stop_all_sounds':
                    track.stop_all_sounds(s['fade'])

                else:
                    self.machine.log.error("TrackPlayer: The specified action "
                                           "is not valid ('%s').", s['action'])

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
                    for key in track_settings:
                        if key not in self.machine.config_validator.get_config_spec()['track_player']:
                            break

                    validated_config[event]['tracks'].update(
                        self._validate_config_item(track, track_settings))

        return validated_config

    def _validate_config_item(self, device, device_settings):
        """Validates the config when in a show"""
        validated_dict = super()._validate_config_item(device, device_settings)
        # device is track name

        # Ensure volume parameter value has been provided for 'set_volume' actions
        if validated_dict[device]['action'] == 'set_volume' and \
                validated_dict[device]['volume'] is None:
            raise ValueError("track_player: 'volume' must be provided for all 'set_volume' "
                             "actions ({} track)".format(device))

        if validated_dict[device]['fade'] < 0:
            raise ValueError("track_player: 'fade' must be greater than or equal to zero for all "
                             "actions ({} track)".format(device))

        return validated_dict

    def clear_context(self, context):
        """Because tracks are persistent for the life of the application, there is nothing
        to clear when the context ends. No new track instances are created using the
        track_player."""
        del context


McPlayerCls = McTrackPlayer
