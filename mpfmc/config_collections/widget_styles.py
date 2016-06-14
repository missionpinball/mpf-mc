from mpfmc.core.config_collection import ConfigCollection


class WidgetStyle(ConfigCollection):

    config_section = 'widget_styles'
    collection = 'widget_styles'
    class_label = 'WidgetStyles'

    def process_config(self, config):
        # config is localized to the 'widget_styles' section
        self.mc.config_validator.validate_config('widget_styles', config,
                                                 add_missing_keys=False)

        return config


collection_cls = WidgetStyle
