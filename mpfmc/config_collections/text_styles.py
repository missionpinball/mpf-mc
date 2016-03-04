from mpfmc.core.config_collection import ConfigCollection


class TextStyle(ConfigCollection):

    config_section = 'text_styles'
    collection = 'text_styles'
    class_label = 'TextStyles'

    def process_config(self, config):
        # config is localized to the 'text_styles' section
        self.mc.config_validator.validate_config('text_styles', config,
                                                 add_missing_keys=False)

        return config


collection_cls = TextStyle
