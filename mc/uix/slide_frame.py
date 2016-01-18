from operator import attrgetter

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import (ScreenManager, NoTransition,
                                    SlideTransition, SwapTransition,
                                    FadeTransition, WipeTransition,
                                    FallOutTransition, RiseInTransition)

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
        self.name = name
        super().__init__()

        super().add_widget(slide_frame)

    def __repr__(self):
        return '<SlideFrameParent name={}>'.format(self.name)

    def add_widget(self, widget):
        widget.config['z'] = abs(widget.config['z'])

        super().add_widget(widget=widget,
                           index=Slide.get_insert_index(
                                   z=abs(widget.config['z']),
                                   target_widget=self))


class SlideFrame(MpfWidget, ScreenManager):

    def __init__(self, mc, name, mode=None):
        self.config = dict()  # this exists for the SlideFrameParent z-order
        self.config['z'] = 0
        self.name = name
        super().__init__(mc=mc, mode=mode)

        mc.targets[name] = self

        self.transition = transition_map['none']()

        self.slide_frame_parent = SlideFrameParent(mc, name, self)

    def __repr__(self):
        return '<SlideFrame name={}, parent={}>'.format(self.name, self.parent)

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

    def remove_slide(self, slide):
        # note there has to be at least one slide, so you can't remove the last
        # one
        if type(slide) is str:
            for s in [x for x in self.screens if x.name == slide]:
                slide = s

        if not isinstance(slide, Slide):
            return

        self.mc.active_slides.pop(slide.name, None)

        if self.current_screen == self.screens[0]:
            try:
                self.current = self.screens[1].name
            except (IndexError, AttributeError):
                pass

        self.remove_widget(slide)
