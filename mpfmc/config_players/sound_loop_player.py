"""Contains the sound loop config player class"""

from copy import deepcopy
from mpfmc.core.mc_config_player import McConfigPlayer


class McSoundLoopPlayer(McConfigPlayer):
    """Base class for the Sound Loop Player that runs on the mpf-mc side of things.
    It receives all of its instructions via BCP from a MpfSoundLoopPlayer instance
    running as part of MPF.

    The sound_loop_player: section of a config file (either the machine-wide or
    a mode-specific config) looks like this:

    sound_loop_player:
        <event_name>:
            <track_name>:
                <sound_loop_set_settings>: ...

    Express config is not supported in the sound_loop_player.

    If you want to control other settings (such as track, priority, volume,
    loops, etc.), enter the track name on the next line and the settings
    indented under it, like this:

    sound_loop_player:
        some_event:
            track_name:
                volume: 0.35
                action: play_layer
                layer: 2

Here are several various examples:

    sound_loop_player:
        some_event:
            loops:
                sound_loop_set: basic_beat
                volume: 0.65

        some_event2:
            loops:
                action: set_volume
                volume: -4.5 db

    """
    config_file_section = 'sound_loop_player'
    show_section = 'sound_loop_sets'
    machine_collection_name = 'sound_loop_sets'

    # pylint: disable=invalid-name
    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Plays a validated section from a sound_loop_player: section of a
        config file or the sound_loops: section of a show.

        The config must be validated.
        """
        del calling_context
        settings = deepcopy(settings)

        self.machine.log.info("SoundLoopPlayer: Play called with settings=%s", settings)

        for track_name, player_settings in settings.items():
            player_settings.update(kwargs)

            track = self.machine.sound_system.audio_interface.get_track_by_name(track_name)

            # Determine action to perform
            if player_settings['action'].lower() == 'play':
                if player_settings['sound_loop_set'] not in self.machine.sound_loop_sets:
                    self.machine.log.error("SoundLoopPlayer: The specified sound loop set "
                                           "does not exist ('{}').".format(player_settings['sound_loop_set']))
                    return
                try:
                    loop_set = self.machine.sound_loop_sets[player_settings['sound_loop_set']]
                    track.play_sound_loop_set(loop_set, context, player_settings)
                except Exception as ex:
                    raise Exception(ex)

            elif player_settings['action'].lower() == 'stop':
                player_settings.setdefault('fade_out', None)
                track.stop_current_sound_loop_set(player_settings['fade_out'])

            elif player_settings['action'].lower() == 'stop_looping':
                track.stop_looping_current_sound_loop_set()

            elif player_settings['action'].lower() == 'jump_to':
                player_settings.setdefault('time', 0)
                track.jump_to_time_current_sound_loop_set(player_settings['time'])

            elif player_settings['action'].lower() == 'set_volume':
                # TODO: Implement setting current loop_set volume
                pass

            elif player_settings['action'].lower() == 'play_layer':
                player_settings.setdefault('volume', None)
                track.play_layer(player_settings['layer'], player_settings['fade_in'], player_settings['timing'],
                                 volume=player_settings['volume'])

            elif player_settings['action'].lower() == 'stop_layer':
                track.stop_layer(player_settings['layer'], player_settings['fade_out'])

            elif player_settings['action'].lower() == 'stop_looping_layer':
                track.stop_looping_layer(player_settings['layer'])

            elif player_settings['action'].lower() == 'set_layer_volume':
                # TODO: Implement setting layer volume
                pass

            else:
                self.machine.log.error("SoundLoopPlayer: The specified action "
                                       "is not valid ('{}').".format(player_settings['action']))

    def get_express_config(self, value):
        """There is no express config for the sound loop player."""
        self.machine.log.error("SoundLoopPlayer: Express config is not supported: "
                               "'{}'".format(value))
        raise AssertionError("Sound Loop Player does not support express config")

    # pylint: disable=too-many-branches
    def validate_config(self, config):
        """Validates the sound_loop_player: section of a config file (either a
        machine-wide config or a mode config).

        Args:
            config: A dict of the contents of the sound_loop_player section
            from the config file. It's assumed that keys are event names, and
            values are settings for what the sound_loop_player should do when
            that event is posted.

        Returns: A dict a validated entries.

        This method overrides the base method since the sound_loop_player has
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
                if self.machine.sound_system.audio_interface.get_track_type(track_name) != "sound_loop":
                    raise ValueError("SoundLoopPlayer: An invalid audio track '{}' is specified for event '{}' "
                                     "(only sound_loop audio tracks are supported).".format(track_name, event))

                validated_config[event].update(self._validate_config_item(track_name, player_settings))

        return validated_config

    def _validate_config_item(self, device, device_settings):
        """Validates the config when in a show or in a player"""

        # event contains the event name that triggers the sound_loop_player action
        # Validate the settings against the config spec

        # First validate the action item (since it will be used to validate the rest
        # of the config)
        if 'action' in device_settings:
            device_settings['action'] = self.machine.config_validator.validate_config_item(
                self.machine.config_validator.config_spec['sound_loop_player']['action'],
                'sound_loop_player:{}'.format(device),
                device_settings['action'])
        else:
            device_settings['action'] = self.machine.config_validator.validate_config_item(
                self.machine.config_validator.config_spec['sound_loop_player']['action'],
                'sound_loop_player:{}'.format(device))

        validated_settings = self.machine.config_validator.validate_config(
            'sound_loop_player_actions:{}'.format(device_settings['action']).lower(),
            device_settings)

        # Remove any items from the settings that were not explicitly provided in the
        # sound_loop_player config section (only want to override sound settings explicitly
        # and not with any default values).  The default values for these items are not
        # legal values and therefore we know the user did not provide them.
        if 'volume' in validated_settings and validated_settings['volume'] is None:
            del validated_settings['volume']
        if 'fade_in' in validated_settings and validated_settings['fade_in'] is None:
            del validated_settings['fade_in']
        if 'fade_out' in validated_settings and validated_settings['fade_out'] is None:
            del validated_settings['fade_out']
        if 'events_when_played' in validated_settings and len(validated_settings['events_when_played']) == 1 and \
                validated_settings['events_when_played'][0] == 'use_sound_loop_setting':
            del validated_settings['events_when_played']
        if 'events_when_stopped' in validated_settings and len(validated_settings['events_when_stopped']) == 1 and \
                validated_settings['events_when_stopped'][0] == 'use_sound_loop_setting':
            del validated_settings['events_when_stopped']
        if 'events_when_looping' in validated_settings and len(validated_settings['events_when_looping']) == 1 and \
                validated_settings['events_when_looping'][0] == 'use_sound_loop_setting':
            del validated_settings['events_when_looping']
        if 'mode_end_action' in validated_settings and (validated_settings['mode_end_action'] is None or
                                                        validated_settings['mode_end_action'] ==
                                                        'use_sound_loop_setting'):
            del validated_settings['mode_end_action']

        validated_dict = dict()
        validated_dict[device] = validated_settings
        return validated_dict

    def clear_context(self, context):
        """Stop all sounds from this context."""
        instance_dict = self._get_instance_dict(context)
        # Iterate over a copy of the dictionary values since it may be modified
        # during the iteration process.
        self.machine.log.debug("SoundLoopPlayer: Clearing context - applying mode_end_action for active sound loop set")
        # TODO: Determine proper action to take while clearing context
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


McPlayerCls = McSoundLoopPlayer
