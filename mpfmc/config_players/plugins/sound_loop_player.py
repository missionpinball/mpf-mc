from mpf.config_players.plugin_player import PluginPlayer


class MpfSoundLoopPlayer(PluginPlayer):
    """Base class for part of the sound loop player which runs as part of MPF.

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF, not the mpf-mc. MPF finds this instance because the mpf-mc setup.py
    has the following entry_point configured:

        sound_loop_player=mpfmc.config_players.sound_loop_player:register_with_mpf

    """
    config_file_section = 'sound_loop_player'
    show_section = 'sound_loop_sets'

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


player_cls = MpfSoundLoopPlayer


def register_with_mpf(machine):
    """Registers the sound loop player plug-in with MPF"""
    return 'sound_loop', MpfSoundLoopPlayer(machine)
