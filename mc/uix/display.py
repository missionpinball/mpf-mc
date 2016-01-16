"""Contains the Display base class, which is a logical display in the
mpf-mc.

"""
from kivy.clock import Clock
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scatter import ScatterPlane

from mc.uix.slide import Slide
from mc.uix.slide_frame import SlideFrame


class Display(ScatterPlane, RelativeLayout):
    displays_to_initialize = 0

    @classmethod
    def display_initialized(cls):
        Display.displays_to_initialize -= 1
        if not Display.displays_to_initialize:
            return True
        else:
            return False

    @staticmethod
    def create_default_display(mc):
        display = Display(mc, 'default', width=1, height=1)
        mc.displays['default'] = display
        mc.default_display = display

    def __init__(self, mc, name, **kwargs):
        self.mc = mc
        self.name = name
        Display.displays_to_initialize += 1

        self.slide_frame = None
        self.native_size = ((kwargs['width'], kwargs['height']))

        self.size_hint = (None, None)
        super().__init__()

        if not self.mc.default_display:
            self.mc.default_display = self

        Clock.schedule_once(self._display_created, 0)

        # Window.bind(system_size=self.on_window_resize)

        # Clock.schedule_once(self.fit_to_window, -1)

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

        self.slide_frame = SlideFrame(self.mc)
        self._slide_frame_created()

    def _slide_frame_created(self, *args):
        # Again we keep waiting here until the new slide manager has been
        # created at the proper size.
        if (self.slide_frame.size[0] != self.native_size[0] or
                    self.slide_frame.size[1] != self.native_size[1]):
            self.slide_frame.size = self.native_size
            Clock.schedule_once(self._slide_frame_created, 0)
            return

        self.add_widget(self.slide_frame)

        Clock.schedule_once(self.show_boot_slide)

        if Display.display_initialized():
            Clock.schedule_once(self.mc.displays_initialized)

    def show_boot_slide(self, *args):
        self.mc.events.post('display_{}_initialized'.format(self.name))

    def _sort_children(self):
        pass

    def on_window_resize(self, window, size):
        self.fit_to_window()

    def fit_to_window(self, *args):
        from kivy.core.window import Window

        self.scale = min(Window.width / self.native_size[0],
                         Window.height / self.native_size[1])
        self.pos = (0, 0)
        self.size = self.native_size

    def add_slide(self, name, config, priority=0):
        Slide(mc=self.mc, name=name, slide_frame=self.slide_frame,
              config=config)

        if priority >= self.slide_frame.current_slide.priority:
            self.slide_frame.current = name
