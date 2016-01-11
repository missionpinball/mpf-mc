from mc.core.config_player import EventPlayer


class WidgetPlayer(EventPlayer):
    config_file_section = 'widget_player'

    def play(self, settings, mode=None):
        if mode and not mode.active:
            return

        if 'screen' in settings:  # add to a named screen
            self.mc.default_display.screens[settings['screen']] \
                ._create_widgets_from_config(
                    mode.config['widgets'][settings['widget']])

        else:  # add this current screen
            self.mc.default_display.screen_manager.current_screen. \
                _create_widgets_from_config(
                    mode.config['widgets'][settings['widget']])
