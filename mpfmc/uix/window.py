from kivy.core.window import Window as KivyWindow
from kivy.clock import Clock
from mpfmc.core.keyboard import Keyboard
from mpfmc.uix.display import Display


class Window(object):

    @staticmethod
    def set_source_display(display):
        KivyWindow.clear()

        for widget in KivyWindow.children:
            KivyWindow.remove_widget(widget)

        KivyWindow.add_widget(display)

        KivyWindow.bind(system_size=display.on_window_resize)
        Clock.schedule_once(display.fit_to_window, -1)

    @staticmethod
    def initialize(mc):
        try:
            mc.icon = mc.machine_config['window']['icon']
        except KeyError:
            mc.icon = 'mc/icons/256x256.png'

        try:
            mc.title = mc.machine_config['window']['title']
        except KeyError:
            mc.title = "Mission Pinball Framework"

        # if there's window: section in the machine config, and if it
        # contains a 'source_display' section, then we'll try to use that.
        # Otherwise we'll use display that has the default target
        try:
            display = mc.displays[mc.machine_config['window'][
                'source_display']]
        except KeyError:
            display = mc.targets['default'].parent
            # print("Selecting source display", display)

        # We need the window to map to a Display instance, so no matter what
        # we're passed, we keep on moving up until we find the actual display.
        while not isinstance(display, Display):
            display = display.parent

        Window.set_source_display(display)

        if 'keyboard' in mc.machine_config:
            mc.keyboard = Keyboard(mc)

