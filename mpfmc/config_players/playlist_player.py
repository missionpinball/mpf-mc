"""Contains the playlist player class"""

from copy import deepcopy
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
    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Plays a validated section from a playlist_player: section of a
        config file or the playlists: section of a show.

        The config must be validated.
        """
        del calling_context
        settings = deepcopy(settings)

        self.machine.log.debug("PlaylistPlayer: Play called with settings=%s", settings)

        for track_name, player_settings in settings.items():
            player_settings.update(kwargs)

            playlist_controller = self.machine.sound_system.audio_interface.get_playlist_controller(track_name)

            # Determine action to perform
            if player_settings['action'].lower() == 'play':
                if player_settings['playlist'] not in self.machine.playlists:
                    self.machine.log.error("PlaylistPlayer: The specified playlist "
                                           "does not exist ('{}').".format(player_settings['playlist']))
                    return
                try:
                    playlist_name = player_settings['playlist']
                    del player_settings['playlist']
                    playlist_controller.play(playlist_name, context, player_settings)
                except Exception as ex:
                    raise Exception(ex)

            elif player_settings['action'].lower() == 'stop':
                player_settings.setdefault('fade_out', None)
                playlist_controller.stop()

            elif player_settings['action'].lower() == 'advance':
                playlist_controller.advance()

            elif player_settings['action'].lower() == 'set_repeat':
                player_settings.setdefault('repeat', True)
                playlist_controller.set_repeat(player_settings['repeat'])

            else:
                self.machine.log.error("SoundLoopPlayer: The specified action "
                                       "is not valid ('{}').".format(player_settings['action']))

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
        validated_config = dict()

        # No need to validate if sound system is not enabled, just return empty dict
        if self.machine.sound_system is None or self.machine.sound_system.audio_interface is None:
            return validated_config

        for event, settings in config.items():
            validated_config[event] = dict()

            for track_name, player_settings in settings.items():

                # Validate the specified track name is a sound_loop track
                playlist_controller = self.machine.sound_system.audio_interface.get_playlist_controller(track_name)
                if playlist_controller is None or \
                        playlist_controller.track is None or \
                        playlist_controller.track.type != "standard":
                    raise ValueError("PlaylistPlayer: An invalid audio track '{}' is specified for event '{}' "
                                     "(only playlist audio tracks are supported).".format(track_name, event))

                validated_config[event].update(self._validate_config_item(track_name, player_settings))

        return validated_config

    def _validate_config_item(self, device, device_settings):
        """Validates the config when in a show or in a player"""

        # event contains the event name that triggers the playlist_player action
        # Validate the settings against the config spec

        # First validate the action item (since it will be used to validate the rest
        # of the config)
        if 'action' in device_settings:
            device_settings['action'] = self.machine.config_validator.validate_config_item(
                self.machine.config_validator.config_spec['playlist_player']['action'],
                'playlist_player:{}'.format(device),
                device_settings['action'])
        else:
            device_settings['action'] = self.machine.config_validator.validate_config_item(
                self.machine.config_validator.config_spec['playlist_player']['action'],
                'playlist_player:{}'.format(device))

        validated_settings = self.machine.config_validator.validate_config(
            'playlist_player_actions:{}'.format(device_settings['action']).lower(),
            device_settings)

        # Remove any items from the settings that were not explicitly provided in the
        # playlist_player config section (only want to override settings explicitly
        # and not with any default values).  The default values for these items are not
        # legal values and therefore we know the user did not provide them.
        if 'crossfade_mode' in validated_settings and validated_settings['crossfade_mode'] == 'use_playlist_setting':
            del validated_settings['crossfade_mode']
        if 'crossfade_time' in validated_settings and validated_settings['crossfade_time'] is None:
            del validated_settings['crossfade_time']
        if 'volume' in validated_settings and validated_settings['volume'] is None:
            del validated_settings['volume']
        if 'fade_in' in validated_settings and validated_settings['fade_in'] is None:
            del validated_settings['fade_in']
        if 'shuffle' in validated_settings and validated_settings['shuffle'] is None:
            del validated_settings['shuffle']
        if 'repeat' in validated_settings and validated_settings['repeat'] is None:
            del validated_settings['repeat']
        if 'scope' in validated_settings and validated_settings['scope'] == 'use_playlist_setting':
            del validated_settings['scope']
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
        validated_dict[device] = validated_settings
        return validated_dict

    def clear_context(self, context):
        """Stop all sounds from this context."""
        self.machine.log.debug("PlaylistPlayer: Clearing context - "
                               "stopping any active playlists started from this context")

        for name in self.machine.sound_system.audio_interface.get_playlist_controller_names():
            playlist_controller = self.machine.sound_system.audio_interface.get_playlist_controller(name)
            if playlist_controller:
                playlist_controller.clear_context(context)


McPlayerCls = McPlaylistPlayer
