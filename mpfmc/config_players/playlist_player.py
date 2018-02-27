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

    The express config just puts a playlist_name next to an event.

    playlist_player:
        some_event: playlist_name_to_play

    If you want to control other settings (such as track, volume,
    loops, etc.), enter the playlist name on the next line and the settings
    indented under it, like this:

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
                playlist = self.machine.playlists[settings['playlist']]
                playlist_controller.play(playlist, settings)
            except Exception as ex:
                raise Exception(ex)

        elif settings['action'].lower() == 'stop':
            settings.setdefault('fade_out', None)
            playlist_controller.stop(settings['fade_out'])

        elif settings['action'].lower() == 'stop_looping':
            playlist_controller.stop_looping()

        elif settings['action'].lower() == 'set_volume':
            pass

        else:
            self.machine.log.error("PlaylistPlayer: The specified action "
                                   "is not valid ('{}').".format(settings['action']))

    def get_express_config(self, value):
        """There is no express config for the sound loop player."""
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

                if self.machine.sound_system.audio_interface.get_track_type(track) != "sound_loop":
                    raise ValueError("PlaylistPlayer: An invalid audio track '{}' is specified for event '{}' "
                                     "(only playlist audio tracks are supported).".format(track, event))
            else:
                raise ValueError("PlaylistPlayer: track is a required setting in event '{}'".format(event))

            validated_config[event].update(self._validate_config_item(track, settings))

        return validated_config

    def _validate_config_item(self, track, track_settings):
        """Validates the config when in a show or in a player"""

        # Validate the settings against the config spec

        # First validate the action item (since it will be used to validate the rest
        # of the config)
        if 'action' in track_settings:
            track_settings['action'] = self.machine.config_validator.validate_config_item(
                self.machine.config_validator.config_spec['sound_loop_player']['common']['action'],
                'sound_loop_player:{}'.format(track),
                track_settings['action'])
        else:
            track_settings['action'] = self.machine.config_validator.validate_config_item(
                self.machine.config_validator.config_spec['sound_loop_player']['common']['action'],
                'sound_loop_player:{}'.format(track))

        validated_dict = self.machine.config_validator.validate_config(
            'sound_loop_player:actions:{}'.format(track_settings['action']).lower(),
            track_settings,
            base_spec='sound_loop_player:common')

        # Remove any items from the settings that were not explicitly provided in the
        # sound_loop_player config section (only want to override sound settings explicitly
        # and not with any default values).  The default values for these items are not
        # legal values and therefore we know the user did not provide them.
        if 'volume' in validated_dict and validated_dict['volume'] is None:
            del validated_dict['volume']
        if 'fade_in' in validated_dict and validated_dict['fade_in'] is None:
            del validated_dict['fade_in']
        if 'fade_out' in validated_dict and validated_dict['fade_out'] is None:
            del validated_dict['fade_out']
        if 'events_when_played' in validated_dict and len(validated_dict['events_when_played']) == 1 and \
                validated_dict['events_when_played'][0] == 'use_sound_loop_setting':
            del validated_dict['events_when_played']
        if 'events_when_stopped' in validated_dict and len(validated_dict['events_when_stopped']) == 1 and \
                validated_dict['events_when_stopped'][0] == 'use_sound_loop_setting':
            del validated_dict['events_when_stopped']
        if 'events_when_looping' in validated_dict and len(validated_dict['events_when_looping']) == 1 and \
                validated_dict['events_when_looping'][0] == 'use_sound_loop_setting':
            del validated_dict['events_when_looping']
        if 'mode_end_action' in validated_dict and (validated_dict['mode_end_action'] is None or
                                                    validated_dict['mode_end_action'] == 'use_sound_loop_setting'):
            del validated_dict['mode_end_action']

        return validated_dict

    def clear_context(self, context):
        """Stop all sounds from this context."""
        instance_dict = self._get_instance_dict(context)
        # Iterate over a copy of the dictionary values since it may be modified
        # during the iteration process.
        self.machine.log.debug("PlaylistPlayer: Clearing context - applying mode_end_action for active sound loop set")
        for sound_instance in list(instance_dict.values()):
            if sound_instance.stop_on_mode_end:
                sound_instance.stop()
            else:
                sound_instance.stop_looping()

        self._reset_instance_dict(context)

    def on_sound_instance_finished(self, sound_instance_id, context, **kwargs):
        """Callback function that is called when a sound instance triggered by the sound_player
        is finished. Remove the specified sound instance from the list of current instances
        started by the sound_player."""
        del kwargs
        instance_dict = self._get_instance_dict(context)
        if sound_instance_id in instance_dict:
            del instance_dict[sound_instance_id]


mc_player_cls = McPlaylistPlayer
