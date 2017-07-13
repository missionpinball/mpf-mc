"""Contains the sound loop config player class"""

from copy import deepcopy
from mpf.core.config_validator import ConfigValidator
from mpfmc.core.mc_config_player import McConfigPlayer


class McSoundLoopPlayer(McConfigPlayer):
    """Base class for the Sound Loop Player that runs on the mpf-mc side of things.
    It receives all of its instructions via BCP from a MpfSoundLoopPlayer instance
    running as part of MPF.

    The sound_loop_player: section of a config file (either the machine-wide or
    a mode-specific config) looks like this:

    sound_loop_player:
        <event_name>:
            <sound_loop_set_name>:
                <sound_loop_set_settings>: ...

    The express config just puts a sound_loop_set_name next to an event.

    sound_loop_player:
        some_event: sound_loop_set_name_to_queue

    If you want to control other settings (such as track, priority, volume,
    loops, etc.), enter the sound loop set name on the next line and the settings
    indented under it, like this:

    sound_loop_player:
        some_event:
            sound_loop_set_name_to_act_upon:
                volume: 0.35
                action: play_layer
                layer: 2

Here are several various examples:

    sound_loop_player:
        some_event:
            basic_beat:
                volume: 0.65

        some_event2:
            another_beat:
                volume: -4.5 db
                action: set_volume

    """
    config_file_section = 'sound_loop_player'
    show_section = 'sound_loops'
    machine_collection_name = 'sound_loop_sets'

    # pylint: disable=invalid-name
    def play(self, settings, context, priority=0, **kwargs):
        """Plays a validated section from a sound_loop_player: section of a
        config file or the sound_loops: section of a show.

        The config must be validated.
        """
        instance_dict = self._get_instance_dict(context)
        settings = deepcopy(settings)
        settings.update(kwargs)

        if 'track' not in settings:
            self.machine.log.error("SoundLoopPlayer: track is a required setting and must be specified.")
            return

        track = self.machine.sound_system.audio_interface.get_track_by_name(settings['track'])

        # Determine action to perform
        if settings['action'].lower() == 'play':
            if settings['sound_loop_set'] not in self.machine.sound_loop_sets:
                self.machine.log.error("SoundLoopPlayer: The specified sound loop set "
                                       "does not exist ('{}').".format(settings['sound_loop_set']))
                return
            try:
                loop_set = self.machine.sound_loop_sets[settings['sound_loop_set']]
                track.play_sound_loop_set(loop_set, settings)
            except Exception as ex:
                raise Exception(ex)

        elif settings['action'].lower() == 'stop':
            settings.setdefault('fade_out', None)
            track.stop_current_sound_loop_set(settings['fade_out'])

        elif settings['action'].lower() == 'stop_looping':
            track.stop_looping_current_sound_loop_set()

        elif settings['action'].lower() == 'set_volume':
            pass
        elif settings['action'].lower() == 'play_layer':
            settings.setdefault('volume', None)
            track.play_layer(settings['layer'], settings['fade_in'], settings['queue'], volume=settings['volume'])

        elif settings['action'].lower() == 'stop_layer':
            track.stop_layer(settings['layer'], settings['fade_out'])

        elif settings['action'].lower() == 'stop_looping_layer':
            track.stop_looping_layer(settings['layer'])

        elif settings['action'].lower() == 'set_layer_volume':
            pass

        else:
            self.machine.log.error("SoundLoopPlayer: The specified action "
                                   "is not valid ('{}').".format(settings['action']))

    def get_express_config(self, value):
        """There is no express config for the sound loop player."""
        del value
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
        # first, we're looking to see if we have a string, a list, or a dict.
        # if it's a dict, we look to see whether we have the name of some sound
        # loop set.

        validated_config = dict()

        for event, settings in config.items():
            validated_config[event] = dict()

            if not isinstance(settings, dict):
                settings = {settings: dict()}
                
            if 'track' in settings:
                track = settings['track']

                if self.machine.sound_system.audio_interface.get_track_type(track) != "sound_loop":
                    raise ValueError("SoundLoopPlayer: An invalid audio track '{}' is specified for event '{}' "
                                     "(only sound_loop audio tracks are supported).".format(track, event))
            else:
                raise ValueError("SoundLoopPlayer: track is a required setting in event '{}'".format(event))

            validated_config[event].update(self._validate_config_item(track, settings))

        return validated_config

    def _validate_config_item(self, track, track_settings):
        """Validates the config when in a show or in a player"""

        # device is sound loop set name
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
        self.machine.log.debug("SoundLoopPlayer: Clearing context - applying mode_end_action for active sound loop set")
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

mc_player_cls = McSoundLoopPlayer
