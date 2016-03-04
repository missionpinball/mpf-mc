from copy import deepcopy

from mpf.config_players.plugin_player import PluginPlayer
from mpfmc.core.mc_config_player import McConfigPlayer


class MpfSlidePlayer(PluginPlayer):
    """Base class for the slide player which runs as part of MPF.

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF, not the mpf-mc. MPF finds this instance because the mpf-mc setup.py has the following
    entry_point configured:

        slide_player=mpfmc.config_players.slide_player:register_with_mpf

    """
    config_file_section = 'slide_player'
    show_section = 'slides'

    def play(self, settings, mode=None, **kwargs):
        super().play(settings, mode, **kwargs)


class McSlidePlayer(McConfigPlayer):
    """Base class for the Slide Player that runs on the mpf-mc side of things.
    It receives all of its instructions via BCP from a MpfSlidePlayer instance
    running as part of MPF.
    """

    config_file_section = 'slide_player'
    show_section = 'slides'
    machine_collection_name = 'slides'


    def play(self, settings, mode=None, caller=None, **kwargs):
        super().play(settings, mode, caller, **kwargs)

        # todo figure out where the settings are coming from and see if we can
        # move the deepcopy there?
        settings = deepcopy(settings)

        if 'slides' in settings:
            settings = settings['slides']

        for slide, s in settings.items():

            if s['target']:
                target = self.machine.targets[s['target']]
            elif mode:
                target = mode.target
            else:
                target = self.machine.targets['default']

            s.update(kwargs)
            s.pop('target', None)
            s.pop('slide', None)

            target.show_slide(slide_name=slide, mode=mode, **s)

    def get_express_config(self, value):
        # express config for slides can either be a string (slide name) or a
        # list (widgets which are put on a new slide)
        if isinstance(value, list):
            return dict(widgets=value)
        else:
            return dict(slide=value)

    def validate_show_config(self, device, device_settings):
        validated_dict = super().validate_show_config(device, device_settings)

        for v in validated_dict.values():

            if 'transition' in v:
                if not isinstance(v['transition'], dict):
                    v['transition'] = dict(type=v['transition'])

                try:
                    v['transition'] = (
                        self.machine.config_validator.validate_config(
                            'transitions:{}'.format(
                                v['transition']['type']), v['transition']))

                except KeyError:
                    raise ValueError('transition: section of config requires a'
                                     ' "type:" setting')

        return validated_dict

player_cls = MpfSlidePlayer
mc_player_cls = McSlidePlayer

def register_with_mpf(machine):
    return 'slide', MpfSlidePlayer(machine)
