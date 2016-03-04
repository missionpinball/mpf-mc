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
    machine_collection_name = None

    def additional_processing(self, config):

        # The config validator is set to ignore the 'transitions' setting,
        # meaning that a value of 'None' is read as string 'None.' However, the
        # user could also entry 'no' or 'false' which would be processed by the
        # YAML processor as NoneType. So we need to look for that and convert
        # it.

        # This code can be used to force No Transition if we implement default
        # transitions in the future
        # if ('transition' in config and
        #             type(config['transition']) is str and
        #             config['transition'].lower() == 'none'):
        #     config['transition'] = dict(type='none')

        if config.get('transition', None):
            config['transition'] = (
                self.machine.config_processor.process_transition(
                        config['transition']))
        else:
            config['transition'] = None

        return config

    def play(self, settings, mode=None, **kwargs):
        super().play(settings, mode, **kwargs)

        print('PLAY SLIDE', settings)


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

        if 'slides' in settings:
            settings = settings['slides']

        for slide, s in settings.items():

            name = s['slide']

            if s['target']:
                target = self.mc.targets[s['target']]
            elif mode:
                target = mode.target
            else:
                target = self.mc.targets['default']

            target.show_slide(slide_name=name, transition=s['transition'],
                              mode=mode, force=s['force'],
                              priority=s['priority'], **kwargs)

    def get_express_config(self, value):
        # express config for slides can either be a string (slide name) or a
        # list (widgets which are put on a new slide)
        if isinstance(value, list):
            return dict(widgets=value, slide=None)
        else:
            return dict(slide=value)

    def validate_config(self, config):
        super().validate_config(config)







player_cls = MpfSlidePlayer
mc_player_cls = McSlidePlayer

def register_with_mpf(machine):
    return 'slide', MpfSlidePlayer(machine)
