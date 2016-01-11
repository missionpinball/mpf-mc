from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scatter import ScatterPlane
from mc.uix.screen import Screen
from mc.uix.screen_manager import ScreenManager


class MpfDisplay(ScatterPlane, RelativeLayout):
    def __init__(self, mc, **kwargs):
        self.mc = mc
        self.screen_manager = None
        self.native_size = ((kwargs['width'], kwargs['height']))

        self.size_hint = (None, None)
        super().__init__(**kwargs)

        Clock.schedule_once(self.display_created, 0)

        Window.bind(system_size=self.on_window_resize)

        Clock.schedule_once(self.fit_to_window, -1)

    def display_created(self, *args):
        if (self.size[0] != self.native_size[0] or
                    self.size[1] != self.native_size[1]):
            self.size = self.native_size
            Clock.schedule_once(self.display_created, 0)
            return

        self.screen_manager = ScreenManager(self.mc)
        self.screen_manager_created()

    def screen_manager_created(self, *args):
        if (self.screen_manager.size[0] != self.native_size[0] or
                    self.screen_manager.size[1] != self.native_size[1]):
            self.screen_manager.size = self.native_size
            Clock.schedule_once(self.screen_manager_created, 0)
            return

        self.add_widget(self.screen_manager)
        Clock.schedule_once(self.mc.display_created)

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
        Screen(name=name, screen_manager=self.screen_manager, config=config)

        if priority >= self.screen_manager.current_screen.priority:
            self.screen_manager.current = name
