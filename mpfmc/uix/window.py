from kivy.core.window import Window as KivyWindow
from mpfmc.core.keyboard import Keyboard
from mpfmc.uix.display import Display
from mpfmc.widgets.display import DisplayWidget

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc     # pylint: disable-msg=cyclic-import,unused-import


class Window:

    @staticmethod
    def set_source_display(display: "DisplayWidget") -> None:
        """Set the source display for the main window."""

        # Clean up any existing objects in the window
        KivyWindow.clear()

        for widget in KivyWindow.children:
            KivyWindow.remove_widget(widget)

        # Add the new display to the window
        KivyWindow.add_widget(display)

        # Make sure the display is re-sized whenever the window changes size
        KivyWindow.bind(system_size=Window.on_size)

    @staticmethod
    def initialize(mc: "MpfMc") -> None:
        mc.icon = mc.machine_config['window']['icon']
        mc.title = mc.machine_config['window']['title']

        # Set the source based on the window: source_display: setting.
        # If that's not valid, and there's a display called "window", use it
        # Otherwise use the default.
        try:
            display = mc.displays[mc.machine_config['window']['source_display']]
        except KeyError:
            display = mc.targets['default']

        # We need the window to map to a Display instance, so no matter what
        # we're passed, we keep on moving up until we find the actual display.
        while not isinstance(display, Display):
            display = display.parent

        config = {
            'type': DisplayWidget.widget_type_name.lower(),
            'source_display': display.name,
            'width': KivyWindow.width,
            'height': KivyWindow.height,
        }

        config = mc.config_validator.validate_config('widgets:{}'.format(
            DisplayWidget.widget_type_name.lower()), config, base_spec='widgets:common')

        if 'effects' in mc.machine_config['window']:
            config['effects'] = mc.effects_manager.validate_effects(mc.machine_config['window']['effects'])

        display_widget = DisplayWidget(mc, config=config)
        display_widget.parent.remove_widget(display_widget)
        Window.set_source_display(display_widget)

        if (display.width / display.height !=
                KivyWindow.width / KivyWindow.height):
            mc.log.warning(
                "ASPECT RATIO MISMATCH: The on-screen window is not the same "
                "aspect ratio as the display called '{}'. The logical display "
                "will be scaled from {}x{} to the window size {}x{}, and a "
                "black bar will make up the difference".format(
                    display.name, display.width, display.height,
                    KivyWindow.width, KivyWindow.height))

        if 'keyboard' in mc.machine_config:
            mc.keyboard = Keyboard(mc)

    @staticmethod
    def on_size(instance, value):
        del instance

        for widget in KivyWindow.children:
            widget.size = value
