from operator import attrgetter

from kivy.uix.screenmanager import (ScreenManager, NoTransition,
                                    SlideTransition, SwapTransition,
                                    FadeTransition, WipeTransition,
                                    FallOutTransition, RiseInTransition)

from mc.uix.slide import Slide

transition_map = dict(none=NoTransition,
                      slide=SlideTransition,
                      swap=SwapTransition,
                      fade=FadeTransition,
                      wipe=WipeTransition,
                      fall_out=FallOutTransition,
                      rise_in=RiseInTransition)


class SlideFrame(ScreenManager):
    def __init__(self, mc, name):
        self.mc = mc
        self.name = name
        super().__init__()

        mc.targets[name] = self

        self.transition = transition_map['none']()

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

    def add_slide(self, name, config, priority=0, show=True, force=False):
        Slide(mc=self.mc, name=name, target=self.name, config=config,
              show=show, force=force, priority=priority)

        if not self.current_screen or priority >= self.current_screen.priority:
            self.current = name

    def add_widget(self, slide, show=True, force=False):
        super().add_widget(screen=slide)

        self._sort_slides()

        if force:
            self.current = slide.name
        elif show:
            self.current = self.screens[0].name

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
