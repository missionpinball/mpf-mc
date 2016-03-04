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

        if 'transition' in config:
            config['transition'] = self.process_transition(
                config['transition'])
        else:
            config['transition'] = None

        return config
        # return SlideDevice(**config)

    def process_transition(self, config):
        # config is localized to the 'transition' section

        if not isinstance(config, dict):
            config = dict(type=config)

        try:
            config = self.mc.config_validator.validate_config(
                    'transitions:{}'.format(config['type']), config)
        except KeyError:
            raise ValueError('transition: section of config requires a '
                             '"type:" setting')

        return config


collection_cls = Slide
