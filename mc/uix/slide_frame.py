from operator import attrgetter

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import (ScreenManager, NoTransition,
                                    SlideTransition, SwapTransition,
                                    FadeTransition, WipeTransition,
                                    FallOutTransition, RiseInTransition,
                                    ScreenManagerException)
from kivy.uix.widget import WidgetException

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

        self.transition = NoTransition()
        # Not implemented yet. Maybe some day?
        # self.default_transition = NoTransition()

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
        if isinstance(value, Slide):
            self._set_current_slide(value)
        elif type(value) is str:
            self._set_current_slide_name(value)

    @property
    def current_slide_name(self):
        """Returns the string name of the current slide."""
        return self.current

    @current_slide_name.setter
    def current_slide_name(self, value):
        """Sets the current slide based on the string name of the slide you
        want to be shown."""
        self._set_current_slide_name(value)

    @property
    def slides(self):
        """List of slide objects of all the active slides for this slide
        frame."""
        return self.screens

    def add_slide(self, name, config, priority=None, mode=None):
        # Note this method just adds it. It doesn't show it.

        # Slide() created also adds it to this screen manager
        return Slide(mc=self.mc, name=name, target=self.name, config=config,
                     mode=mode, priority=priority)

    def show_slide(self, slide_name, transition=None, mode=None, force=False,
                   priority=None):

        try:  # does this slide exist in this screen manager already?
            slide = self.get_screen(slide_name)
        except ScreenManagerException:  # create it if not
            slide = self.add_slide(name=slide_name,
                                   config=self.mc.slide_configs[slide_name],
                                   priority=priority,
                                   mode=mode)

        if slide.priority >= self.current_slide.priority or force:
            # We need to show this slide

            # Have to set a transition even if there's not one because we have
            # to remove whatever transition was last used
            self.transition = self.mc.transition_manager.get_transition(
                    transition)

            self._set_current_slide(slide)
            return True

        else:  # Not showing this slide
            return False

    def remove_slide(self, slide, transition_config=None):
        # note there has to be at least one slide, so you can't remove the last
        # one

        # warning, if you just created a slide, you have to wait at least on
        # tick before removing it. Can we prevent that? What if someone tilts
        # at the exact perfect instant when a mode was starting or something?

        # maybe we make sure to run a kivy tick between bcp reads or something?

        try:
            slide = self.get_screen(slide)
        except ScreenManagerException:  # no slide by that name
            if not isinstance(slide, Slide):
                return

        if len(self.screens) == 1:
            return

        for widget in self.children:
            widget.prepare_for_removal()

        self.mc.active_slides.pop(slide.name, None)

        # If the current screen is the active one, find the next highest
        # priority one to show instead.
        if self.current_screen == slide:
            new_slide = self.get_next_highest_slide(slide)
            self.transition = self.mc.transition_manager.get_transition(
                transition_config)
            self._set_current_slide(new_slide)

        try:
            self.remove_widget(slide)
        except WidgetException:
            pass

    def _set_current_slide(self, slide):
        # I think there's a bug in Kivy 1.9.1. According to the docs, you
        # should be able to set self.current to a screen name. But if that
        # screen is already managed by this screen manager, it will raise
        # an exception, and the source is way deep in their code and not
        # easy to fix by subclassing. So this is sort of a hack that looks
        # for that exception, and if it sees it, it just removes and
        # re-adds the screen.
        try:
            self.current = slide.name
        except WidgetException:
            self.remove_widget(slide)
            self.add_widget(slide)
            self.current = slide.name

    def _set_current_slide_name(self, slide_name):
        try:
            self._set_current_slide(self.get_screen(slide_name))
        except ScreenManagerException:
            raise ValueError('Cannot set current slide to "{}" as there is '
                             'no slide in this slide_frame with that '
                             'name'.format(slide_name))

    def get_next_highest_slide(self, slide):
        # TODO This should be a list comprehension?

        new_slide = None

        for s in self.slides:
            if s == slide:
                continue
            elif not new_slide:
                new_slide = s
            elif s.priority > new_slide.priority:
                new_slide = s
            elif (s.priority == new_slide.priority and
                    s.creation_order > new_slide.creation_order):
                new_slide = s

        return new_slide
