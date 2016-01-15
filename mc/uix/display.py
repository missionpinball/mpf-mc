"""Contains the MpfDisplay base class, which is a logical display in the
mpf-mc.

"""
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scatter import ScatterPlane

from mc.uix.screen import Screen
from mc.uix.screen_manager import ScreenManager


# TODO how does this display know it's in a window?


class MpfDisplay(ScatterPlane, RelativeLayout):

    displays_to_initialize = 0

    @classmethod
    def display_initialized(cls):
        MpfDisplay.displays_to_initialize -= 1
        if not MpfDisplay.displays_to_initialize:
            return True
        else:
            return False


    def __init__(self, mc, **kwargs):
        self.mc = mc
        MpfDisplay.displays_to_initialize += 1

        self.screen_manager = None
        self.native_size = ((kwargs['width'], kwargs['height']))

        self.size_hint = (None, None)
        super().__init__()

        if not self.mc.default_display:
            self.mc.default_display = self

        Clock.schedule_once(self._display_created, 0)

        Window.bind(system_size=self.on_window_resize)

        Clock.schedule_once(self.fit_to_window, -1)

    def _display_created(self, *args):
        # There's a race condition since mpf-mc will continue while the display
        # gets setup. So we need to wait to know that the display is done.
        # Easiest way to do that is to check to see if the display is the right
        # size, and when it is, we move on.
        if (self.size[0] != self.native_size[0] or
                    self.size[1] != self.native_size[1]):
            self.size = self.native_size
            Clock.schedule_once(self._display_created, 0)
            return

        self.screen_manager = ScreenManager(self.mc)
        self._screen_manager_created()

    def _screen_manager_created(self, *args):
        # Again we keep waiting here until the new screen manager has been
        # created at the proper size.
        if (self.screen_manager.size[0] != self.native_size[0] or
                    self.screen_manager.size[1] != self.native_size[1]):
            self.screen_manager.size = self.native_size
            Clock.schedule_once(self._screen_manager_created, 0)
            return

        self.add_widget(self.screen_manager)

        Clock.schedule_once(self.show_boot_screen)

        if MpfDisplay.display_initialized():
            Clock.schedule_once(self.mc.displays_initialized)

    def show_boot_screen(self, *args):
        if 'screens' in self.mc.machine_config and 'boot' in \
                self.mc.machine_config[
            'screens']:
            Screen(name='boot',
                   screen_manager=self.screen_manager,
                   config=self.mc.machine_config['screens']['boot'])

            self.screen_manager.current = 'boot'

    def _sort_children(self):
        pass

    def on_window_resize(self, window, size):
        self.fit_to_window()

    def fit_to_window(self, *args):
        self.scale = min(Window.width / self.native_size[0],
                         Window.height / self.native_size[1])
        self.pos = (0, 0)
        self.size = self.native_size

    def add_screen(self, name, config, priority=0):
        Screen(mc = self.mc, name=name, screen_manager=self.screen_manager, \
                                             config=config)

        if priority >= self.screen_manager.current_screen.priority:
            self.screen_manager.current = name
