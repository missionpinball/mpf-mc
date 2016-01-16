from mc.core.config_player import ConfigPlayer


class WidgetPlayer(ConfigPlayer):
    config_file_section = 'widget_player'

    def play(self, settings, mode=None):
        if mode and not mode.active:
            return

        if 'slide' in settings:  # add to a named slide
            self.mc.default_display.slides[settings['slide']] \
                ._create_widgets_from_config(
                    mode.config['widgets'][settings['widget']])

        else:  # add this current slide
            self.mc.default_display.slide_frame.current_slide. \
                _create_widgets_from_config(
                    mode.config['widgets'][settings['widget']])
