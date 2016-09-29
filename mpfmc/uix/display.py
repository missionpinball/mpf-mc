"""Contains the Display base class, which is a logical display in the
mpf-mc.

"""
from kivy.clock import Clock
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scatter import Scatter
from mpfmc.uix.slide_frame import SlideFrame


class Display(Scatter, RelativeLayout):
    displays_to_initialize = 0

    @staticmethod
    def create_default_display(mc):
        Display(mc, 'default', width=1, height=1)

    def __init__(self, mc, name, **kwargs):
        self.mc = mc
        self.name = name
        self.config = kwargs
        Display.displays_to_initialize += 1

        self.slide_frame = None
        self.native_size = (self.config['width'], self.config['height'])

        self.size_hint = (None, None)

        super().__init__()
        Clock.schedule_once(self._display_created, 0)

    def __repr__(self):
        return '<Display name={}, size={}x{}>'.format(self.name,
                                                      self.native_size[0],
                                                      self.native_size[1])

    @property
    def current_slide(self):
        return self.slide_frame.current_slide

    @current_slide.setter
    def current_slide(self, value):
        self.slide_frame.current_slide = value

    @property
    def current_slide_name(self):
        return self.slide_frame.current_slide_name

    @current_slide_name.setter
    def current_slide_name(self, value):
        self.slide_frame.current_slide_name = value

    def _display_created(self, *args):
        del args
        # There's a race condition since mpf-mc will continue while the display
        # gets setup. So we need to wait to know that the display is done.
        # Easiest way to do that is to check to see if the display is the right
        # size, and when it is, we move on.
        if (self.size[0] != self.native_size[0] or
                self.size[1] != self.native_size[1]):
            self.size = self.native_size
            Clock.schedule_once(self._display_created, 0)
            return

        config = dict(width=self.native_size[0], height=self.native_size[1],
                      style=None)

        self.slide_frame = SlideFrame(mc=self.mc, name=self.name,
                                      config=config)

        self.slide_frame_created()

    def slide_frame_created(self, *args):
        del args
        self.add_widget(self.slide_frame.slide_frame_parent)
        self.mc.displays[self.name] = self
        self._set_default_target()

        Clock.schedule_once(self._init_done, 0)

    def _set_default_target(self):
        try:
            if self.config['default']:
                self.mc.targets['default'] = self.slide_frame
        except KeyError:
            pass

    def _init_done(self, *args):
        del args
        self.mc.post_mc_native_event('display_{}_initialized'.format(self.name))
        '''event: display_(name)_initialized
        desc: The display called (name) has been initialized. This event is
        generated in the MC, so it won't be sent to MPF if the MC is started up
        and ready first.

        This event is part of the MPF-MC boot process and is not particularly
        useful for game developers. If you want to show a "boot" slide as
        early as possible, use the *mc_ready* event.
        '''

        Display.displays_to_initialize -= 1

        if not Display.displays_to_initialize:
            Clock.schedule_once(self._displays_initialized)

    def _displays_initialized(self, *args):
        del args

        if len(self.mc.displays) == 1:
            self.mc.targets['default'] = \
                [x for x in self.mc.displays.values()][0].slide_frame

        elif 'default' not in self.mc.targets:
            for target in ('window', 'dmd'):
                if target in self.mc.targets:
                    self.mc.targets['default'] = self.mc.targets[target]
                    break

            if 'default' not in self.mc.targets:
                self.mc.targets['default'] = self.mc.displays[
                    (sorted(self.mc.displays.keys()))[0]].slide_frame

        self.mc.displays_initialized()

    def _sort_children(self):
        pass

    def on_window_resize(self, window, size):
        del window
        del size
        self.fit_to_window()

    def fit_to_window(self, *args):
        del args
        from kivy.core.window import Window

        self.scale = min(Window.width / self.native_size[0],
                         Window.height / self.native_size[1])
        self.pos = (0, 0)
        self.size = self.native_size
