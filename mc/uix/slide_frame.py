from operator import attrgetter

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import (ScreenManager, NoTransition,
                                    SlideTransition, SwapTransition,
                                    FadeTransition, WipeTransition,
                                    FallOutTransition, RiseInTransition)

from mc.core.utils import set_position, get_insert_index
from mc.uix.slide import Slide
from mc.uix.widget import MpfWidget

transition_map = dict(none=NoTransition,
                      slide=SlideTransition,
                      swap=SwapTransition,
                      fade=FadeTransition,
                      wipe=WipeTransition,
                      fall_out=FallOutTransition,
                      rise_in=RiseInTransition)


class SlideFrameParent(FloatLayout):
    def __init__(self, mc, name, slide_frame):
        self.mc = mc
        self.name = slide_frame.name

        self.ready = False
        self.size_hint = (None, None)
        super().__init__()
        self.size = slide_frame.native_size
        self.add_widget(slide_frame)

    def __repr__(self):
        return '<SlideFrameParent name={}, parent={}>'.format(self.name,
                                                              self.parent)

    def add_widget(self, widget):
        widget.config['z'] = abs(widget.config['z'])

        super().add_widget(widget=widget,
                           index=get_insert_index(z=abs(widget.config['z']),
                                                  target_widget=self))

    def on_size(self, *args):
        for widget in self.children:
            widget.pos = set_position(self.width, self.height,
                                      widget.width, widget.height)


class SlideFrame(MpfWidget, ScreenManager):
    def __init__(self, mc, name=None, config=None, slide=None, mode=None):

        self.name = name  # needs to be set before super()

        # If this is a the main SlideFrame of a display, it will get its size
        # from its parent. If this is a widget, it will get its size from
        # the config.
        try:
            self.native_size = (config['width'], config['height'])
        except (KeyError, TypeError):
            self.native_size = self.slide.native_size

        super().__init__(mc=mc, mode=mode, slide=slide, config=config)
        self.slide_frame_parent = None
        # self.init_callback = init_callback

        # minimal config needed if this is a widget
        if not config:
            self.config = dict()

        if 'z' not in self.config:
            self.config['z'] = 0

        self.transition = transition_map['none']()

        self.slide_frame_parent = SlideFrameParent(mc, name, self)
        self.slide_frame_parent.config = self.config

        self.mc.targets[self.name] = self

    def __repr__(self):
        return '<SlideFrame name={}, current slide={}, total slides={' \
               '}>'.format(
                self.name, self.current_slide_name, len(self.screens))

    @property
    def current_slide(self):
        """Returns the Slide object of the current slide."""
        return self.current_screen

    @current_slide.setter
    def current_slide(self, value):
        """Sets the current slide. You can set it to a Slide object or a
        string of the slide name."""
        if isinstance(value, Slide) and value in self.slides:
            self.current = value.name
        elif type(value) is str:
            self.current = value

    @property
    def current_slide_name(self):
        """Returns the string name of the current slide."""
        return self.current

    @current_slide_name.setter
    def current_slide_name(self, value):
        """Sets the current slide based on the string name of the slide you
        want to be shown."""
        self.current = value

    @property
    def slides(self):
        """List of slide objects of all the active slides for this slide
        frame."""
        return self.screens

    def get_slide_by_name(self, slide_name):
        for slide in [x for x in self.screens if x.name == slide_name]:
            return slide

    def add_slide(self, name, config, priority=0, mode=None, show=True,
                  force=False):
        Slide(mc=self.mc, name=name, target=self.name, config=config,
              mode=mode, show=show, force=force, priority=priority)

        if not self.current_screen or priority >= self.current_screen.priority:
            self.current = name

    def add_widget(self, slide, show=True, force=False):
        super().add_widget(screen=slide)

        self._sort_slides()

        if force:
            self.current = slide.name
        elif show:
            self.show_current_slide()

    def _sort_slides(self):
        # sort reverse order by priority, then by creation order (so if two
        # slides have the same priority, the newest one is higher priority.
        self.screens = sorted(self.screens, key=attrgetter('creation_order'),
                              reverse=True)
        self.screens = sorted(self.screens, key=attrgetter('priority'),
                              reverse=True)

    def show_current_slide(self):
        if self.screens[0] != self.current_screen:
            self.current = self.screens[0].name

    def show_slide(self, slide_name, force=False):
        slide = self.get_slide_by_name(slide_name)

        if slide and (slide.priority <= self.current_slide.priority or force):
            self.current_slide = slide_name
            return True

        else:
            return False

    def remove_slide(self, slide):
        # note there has to be at least one slide, so you can't remove the last
        # one
        if type(slide) is str:
            for s in [x for x in self.screens if x.name == slide]:
                slide = s

        if not isinstance(slide, Slide):
            return

        if len(self.slides) == 1:
            return

        for widget in self.children:
            widget.prepare_for_removal()

        self.mc.active_slides.pop(slide.name, None)

        # TODO is this right? Is the screens list in priority order
        if self.current_screen == self.screens[0]:
            try:
                self.current = self.screens[1].name
            except (IndexError, AttributeError):
                pass

        self.remove_widget(slide)

        # TODO check for memory leak. Should probably convert everything else
        # to a weakref / proxyref
