"""Contains the playlist player class"""

from copy import deepcopy
from mpf.core.config_validator import ConfigValidator
from mpfmc.core.mc_config_player import McConfigPlayer


class McPlaylistPlayer(McConfigPlayer):
    """Base class for the Playlist Player that runs on the mpf-mc side of things.
    It receives all of its instructions via BCP from a MpfPlaylistPlayer instance
    running as part of MPF.

    The playlist_player: section of a config file (either the machine-wide or
    a mode-specific config) looks like this:

    playlist_player:
        <event_name>:
            <playlist_track_name>:
                <playlist_settings>: ...

    Express config is not supported in the playlist player.

    To control other settings (such as track, action, etc.), enter the playlist name on
    the next line and the settings indented under it, like this:

    playlist_player:
        some_event:
            playlist_track_name:
                action: advance

Here are several various examples:

    playlist_player:
        some_event:
            playlist:
                playlist: attract_mode_music
                volume: 0.65

        some_event2:
            playlist:
                action: stop
                fade-out: 2s

    """
    
    config_file_section = 'playlist_player'
    show_section = 'playlists'
    machine_collection_name = 'playlists'

    # pylint: disable=invalid-name
    def play(self, settings, context, priority=0, **kwargs):
        """Plays a validated section from a playlist_player: section of a
        config file or the playlists: section of a show.

        The config must be validated.
        """
        instance_dict = self._get_instance_dict(context)
        settings = deepcopy(settings)
        settings.update(kwargs)

        if 'track' not in settings:
            self.machine.log.error("PlaylistPlayer: track is a required setting and must be specified.")
            return

        playlist_controller = self.machine.sound_system.audio_interface.get_playlist_controller(settings['track'])
        if playlist_controller is None:
            self.machine.log.error("PlaylistPlayer: track must refer to an existing audio playlist track.")
            return

        # Determine action to perform
        if settings['action'].lower() == 'play':
            if settings['playlist'] not in self.machine.playlists:
                self.machine.log.error("PlaylistPlayer: The specified playlist "
                                       "does not exist ('{}').".format(settings['playlist']))
                return
            try:
                playlist_controller.play(settings['playlist'], context, settings)
            except Exception as ex:
                raise Exception(ex)

        elif settings['action'].lower() == 'stop':
            settings.setdefault('fade_out', None)
            playlist_controller.stop(settings['fade_out'])

        elif settings['action'].lower() == 'set_repeat':
            settings.setdefault('repeat', True)
            playlist_controller.repeat = settings['repeat']

        elif settings['action'].lower() == 'set_volume':
            pass

        else:
            self.machine.log.error("PlaylistPlayer: The specified action "
                                   "is not valid ('{}').".format(settings['action']))

    def get_express_config(self, value):
        """There is no express config for the playlist player."""
        del value
        raise AssertionError("Playlist Player does not support express config")

    # pylint: disable=too-many-branches
    def validate_config(self, config):
        """Validates the playlist_player: section of a config file (either a
        machine-wide config or a mode config).

        Args:
            config: A dict of the contents of the playlist_player section
            from the config file. It's assumed that keys are event names, and
            values are settings for what the playlist_player should do when
            that event is posted.

        Returns: A dict a validated entries.

        This method overrides the base method since the playlist_player has
        unique options.

        """
        # first, we're looking to see if we have a string, a list, or a dict.
        # if it's a dict, we look to see whether we have the name of some sound
        # loop set.

        validated_config = dict()

        # No need to validate if sound system is not enabled, just return empty dict
        if self.machine.sound_system is None or self.machine.sound_system.audio_interface is None:
            return validated_config

        for event, settings in config.items():
            validated_config[event] = dict()

            if not isinstance(settings, dict):
                settings = {settings: dict()}

            if 'track' in settings:
                track = settings['track']

                playlist_controller = self.machine.sound_system.audio_interface.get_playlist_controller(track)
                if playlist_controller is None:
                    raise ValueError("PlaylistPlayer: An invalid audio track '{}' is specified for event '{}' "
                                     "(only playlist audio tracks are supported).".format(track, event))
            else:
                raise ValueError("PlaylistPlayer: track is a required setting in event '{}'".format(event))

            validated_config[event].update(self._validate_config_item(track, settings))

        return validated_config

    def _validate_config_item(self, track_name, player_settings):
        """Validates the config when in a show or in a player"""

        # event contains the event name that triggers the playlist_player action
        # Validate the settings against the config spec

        # First validate the action item (since it will be used to validate the rest
        # of the config)
        if 'action' in player_settings:
            player_settings['action'] = self.machine.config_validator.validate_config_item(
                self.machine.config_validator.config_spec['playlist_player']['action'],
                'playlist_player:{}'.format(track_name),
                player_settings['action'])
        else:
            player_settings['action'] = self.machine.config_validator.validate_config_item(
                self.machine.config_validator.config_spec['playlist_player']['action'],
                'playlist_player:{}'.format(track_name))

        validated_settings = self.machine.config_validator.validate_config(
            'playlist_player_actions:{}'.format(player_settings['action']).lower(),
            player_settings)

        # Remove any items from the settings that were not explicitly provided in the
        # playlist_player config section (only want to override settings explicitly
        # and not with any default values).  The default values for these items are not
        # legal values and therefore we know the user did not provide them.
        if 'volume' in validated_settings and validated_settings['volume'] is None:
            del validated_settings['volume']
        if 'fade_in' in validated_settings and validated_settings['fade_in'] is None:
            del validated_settings['fade_in']
        if 'events_when_played' in validated_settings and len(validated_settings['events_when_played']) == 1 and \
                validated_settings['events_when_played'][0] == 'use_playlist_setting':
            del validated_settings['events_when_played']
        if 'events_when_stopped' in validated_settings and len(validated_settings['events_when_stopped']) == 1 and \
                validated_settings['events_when_stopped'][0] == 'use_playlist_setting':
            del validated_settings['events_when_stopped']
        if 'events_when_looping' in validated_settings and len(validated_settings['events_when_looping']) == 1 and \
                validated_settings['events_when_looping'][0] == 'use_playlist_setting':
            del validated_settings['events_when_looping']
        if 'events_when_sound_changed' in validated_settings and len(
                validated_settings['events_when_sound_changed']) == 1 and \
                validated_settings['events_when_sound_changed'][0] == 'use_playlist_setting':
            del validated_settings['events_when_sound_changed']
        if 'events_when_sound_stopped' in validated_settings and len(
                validated_settings['events_when_sound_stopped']) == 1 and \
                validated_settings['events_when_sound_stopped'][0] == 'use_playlist_setting':
            del validated_settings['events_when_sound_stopped']

        validated_dict = dict()
        validated_dict[track_name] = validated_settings
        return validated_dict

    def clear_context(self, context):
        """Stop all sounds from this context."""
        instance_dict = self._get_instance_dict(context)
        # Iterate over a copy of the dictionary values since it may be modified
        # during the iteration process.
        self.machine.log.debug("PlaylistPlayer: Clearing context")
        # TODO: clear context on playlist track(s)

        self._reset_instance_dict(context)


mc_player_cls = McPlaylistPlayer
