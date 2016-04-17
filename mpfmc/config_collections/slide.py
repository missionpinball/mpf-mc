from mpfmc.core.config_collection import ConfigCollection


class Slide(ConfigCollection):

    config_section = 'slides'
    collection = 'slides'
    class_label = 'SlideConfig'

    def process_config(self, config):
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
            config['widgets'][i] = self.mc.widgets.process_widget(widget)

        config = self.mc.config_validator.validate_config('slides', config)
        config = self.mc.transition_manager.validate_transitions(config)

        return config


collection_cls = Slide
