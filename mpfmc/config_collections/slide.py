from typing import Union
from mpfmc.core.config_collection import ConfigCollection


class SlideCollection(ConfigCollection):

    config_section = 'slides'
    collection = 'slides'
    class_label = 'SlideConfig'

    def process_config(self, config: Union[dict, list]) -> dict:
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
                if config['widgets']:
                    config['widgets'] = [config['widgets']]
                else:
                    config['widgets'] = []

        for i, widget in enumerate(config['widgets']):
            # since dict is mutable it updates in place
            config['widgets'][i] = self.mc.widgets.process_widget(widget)

        config = self.mc.config_validator.validate_config('slides', config)
        config = self.mc.transition_manager.validate_transitions(config)

        return config

    def validate_config(self, config):
        # since dict is mutable it updates in place
        self.mc.widgets.validate_config(config['widgets'])


CollectionCls = SlideCollection
