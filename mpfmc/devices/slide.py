from collections import namedtuple

from mpfmc.core.device import Device
from mpfmc.devices.widget import Widget

SlideDevice = namedtuple('SlideDevice',
                          'widgets transition tags label mode',
                         verbose=False)

class Slide(Device):

    config_section = 'slides'
    collection = 'slides'
    class_label = 'SlideConfig'

    @classmethod
    def process_config(cls, config):
        # config is localized to an single slide name entry

        if isinstance(config, list):
            new_dict = dict()
            new_dict['widgets'] = config
            config = new_dict

        elif isinstance(config, dict):
            if 'widgets' not in config:
                new_dict = dict()
                new_dict['widgets'] = [config]
                config = new_dict

            elif not isinstance(config['widgets'], list):
                config['widgets'] = [config['widgets']]

        for i, widget in enumerate(config['widgets']):
            # since dict is mutable it updates in place
            config['widgets'][i] = Widget.process_widget(widget)

        if 'transition' in config:
            config['transition'] = cls.process_transition(config['transition'])

        return config
        # return SlideDevice(**config)

    @classmethod
    def process_transition(cls, config):
        # config is localized to the 'transition' section

        if not isinstance(config, dict):
            config = dict(type=config)

        try:
            config = cls.mc.config_validator.validate_config(
                    'transitions:{}'.format(config['type']), config)
        except KeyError:
            raise ValueError('transition: section of config requires a '
                             '"type:" setting')

        return config
