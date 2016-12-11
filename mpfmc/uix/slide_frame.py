from bisect import bisect_left

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import (ScreenManager, NoTransition,
                                    SlideTransition, SwapTransition,
                                    FadeTransition, WipeTransition,
                                    FallOutTransition, RiseInTransition,
                                    ScreenManagerException)
from kivy.uix.stencilview import StencilView
from kivy.uix.widget import WidgetException

from mpfmc.core.utils import set_position
from mpfmc.uix.slide import Slide
from mpfmc.uix.widget import MpfWidget

transition_map = dict(none=NoTransition,
                      slide=SlideTransition,
                      swap=SwapTransition,
                      fade=FadeTransition,
                      wipe=WipeTransition,
                      fall_out=FallOutTransition,
                      rise_in=RiseInTransition)


class SlideFrameParent(MpfWidget, FloatLayout):

    """Parent of a slide frame."""

    def __init__(self, mc, config, slide_frame, **kwargs):
        del kwargs
        self.mc = mc
        self.name = slide_frame.name
        self.config = config
        self.slide_frame = slide_frame

        self.ready = False
        self.size_hint = (None, None)
        super().__init__(mc=mc, key=None, config=config)
        self.size = slide_frame.native_size

        self.stencil = StencilView(size_hint=(None, None),
                                   size=self.size)
        self.stencil.config = dict()
        self.stencil.config['z'] = 0
        super().add_widget(self.stencil)
        self.add_widget(slide_frame)

    def __repr__(self):
        return '<SlideFrameParent name={}, parent={}>'.format(self.name,
                                                              self.parent)

    def on_pos(self, *args):

        # if this is the initial positioning, calculate it from the config
        # otherwise just update the slide frame and stencil

        if not self.slide_frame.pos:
            self.pos = set_position(self.parent.width,
                                    self.parent.height,
                                    self.width, self.height,
                                    self.slide_frame.config['x'],
                                    self.slide_frame.config['y'],
                                    self.slide_frame.config['anchor_x'],
                                    self.slide_frame.config['anchor_y'])

        self.stencil.pos = self.pos
        self.slide_frame.pos = self.pos

    def add_widget(self, widget, **kwargs):
        del kwargs

        widget.pos = set_position(self.width, self.height,
                                  widget.width, widget.height)

        self.stencil.add_widget(widget, bisect_left(
            self.stencil.children, widget))

    def prepare_for_removal(self):
        """Remove slide frame from targets."""
        super().prepare_for_removal()
        self.mc.targets[self.name].prepare_for_removal()
        del self.mc.targets[self.name]


class SlideFrame(MpfWidget, ScreenManager):

    """A widget which displays slides."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, mc, name=None, config=None, key=None, play_kwargs=None, **kwargs):
        del play_kwargs
        del kwargs
        self.name = name  # needs to be set before super()
        # If this is a the main SlideFrame of a display, it will get its size
        # from its parent. If this is a widget, it will get its size from
        # the config.
        try:
            self.native_size = (config['width'], config['height'])
        except (KeyError, TypeError):
            self.native_size = self.parent.native_size

        super().__init__(mc=mc, config=config, key=key)

        # minimal config needed if this is a widget
        if not config:
            self.config = dict()
        if 'x' not in config:
            self.config['x'] = None
        if 'y' not in config:
            self.config['y'] = None
        if 'anchor_y' not in config:
            self.config['anchor_y'] = 'middle'
        if 'anchor_x' not in config:
            self.config['anchor_x'] = 'center'
        if 'z' not in self.config:
            self.config['z'] = 0

        self.transition = NoTransition()

        self.slide_frame_parent = SlideFrameParent(mc, self.config, self)
        self.slide_frame_parent.config = self.config

        self.mc.targets[self.name] = self

        # create a blank slide for this display. Why?
        # 1. sometimes people try to play widgets with no slide. This makes
        # that work.
        # 2. the first slide that's created and added to this frame will be
        # automatically show, which we don't want. Also we want to ensure that
        # our slide event will be called which only happens when this slide is
        # switched to, rather than automatically added.
        self._set_current_slide(None)

        self._flag_slide_changed = False

        self.mc.post_mc_native_event('display_{}_ready'.format(self.name))
        '''event: display_(name)_ready
        desc: The display target called (name) is now ready and available to
        show slides.

        This event is useful with slide_frame widgets where you want to add
        a slide_frame to an existing slide which shows some content, but you
        need to make sure the slide_frame exists before showing a slide.

        So if you have a slide_frame called "overlay", then you can add it to
        a slide however you want, and when it's added, the event
        "display_overlay_ready" will be posted, and then you can use that event
        in your slide_player to trigger the first slide you want to show.

        Note that this event is posted by MPF-MC and will not exist on the MPF
        side. So you can use this event for slide_player, widget_player, etc.,
        but not to start shows or other things controlled by MPF.'''

    def __repr__(self):
        return '<SlideFrame {}{}, current slide={}, total slides={}>'.format(
            self.name, self.size, self.current_slide_name,
            len(self.screens))

    @property
    def current_slide(self):
        """Returns the Slide object of the current slide."""
        return self.current_screen

    @current_slide.setter
    def current_slide(self, value):
        """Set the current slide.

        You can set it to a Slide object or a string of the slide name.
        """
        if isinstance(value, Slide):
            self._set_current_slide(value)
        elif isinstance(value, str):
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
        """Return list of slide objects of all the active slides for this slide frame."""
        return self.screens

    # pylint: disable-msg=too-many-arguments
    def add_slide(self, name, config=None, priority=0, key=None, play_kwargs=None):
        # Note this method just adds it. It doesn't show it.

        try:
            return self.get_screen(name)
        except ScreenManagerException:
            # Slide() created also adds it to this screen manager
            return Slide(mc=self.mc, name=name, target=self.name,
                         config=config, key=key, priority=priority,
                         play_kwargs=play_kwargs)

    # pylint: disable-msg=too-many-arguments
    def show_slide(self, slide_name, transition=None, key=None, force=False,
                   priority=0, show=True, expire=None, play_kwargs=None,
                   **kwargs):

        if not play_kwargs:
            play_kwargs = kwargs
        else:
            play_kwargs.update(kwargs)

        try:  # does this slide exist in this screen manager already?
            slide = self.get_screen(slide_name)
        except ScreenManagerException:  # create it if not
            slide = self.add_slide(name=slide_name,
                                   config=self.mc.slides[slide_name],
                                   priority=priority,
                                   key=key,
                                   play_kwargs=play_kwargs)

        # update the widgets with whatever kwargs came through here
        if play_kwargs:
            for widget in slide.walk():
                try:
                    widget.update_kwargs(**play_kwargs)
                except AttributeError:
                    pass

        if not transition:
            try:  # anon slides are in the collection
                transition = self.mc.slides[slide_name]['transition']
            except KeyError:
                pass

        # If there's an expire kwarg, that takes priority over slide's expire
        if expire:
            slide.schedule_removal(expire)
        elif slide.expire:
            slide.schedule_removal(slide.expire)

        if (slide.priority >= self.current_slide.priority and show) or force:
            # We need to show this slide

            # Have to set a transition even if there's not one because we have
            # to remove whatever transition was last used
            self.transition = self.mc.transition_manager.get_transition(
                transition)

            self._set_current_slide(slide)
            return True

        else:  # Not showing this slide
            return False

    # pylint: disable-msg=too-many-arguments
    def add_and_show_slide(self, widgets=None, slide_name=None,
                           transition=None, priority=0, key=None,
                           force=False, expire=None, play_kwargs=None,
                           **kwargs):
        # create the slide. If a slide with this name already exists, it will
        # be replaced

        if not play_kwargs:
            play_kwargs = kwargs
        else:
            play_kwargs.update(kwargs)

        slide_obj = self.add_slide(name=slide_name,
                                   config=dict(widgets=widgets),
                                   priority=priority, key=key)

        self.show_slide(slide_name=slide_obj.name, transition=transition,
                        priority=priority, force=force,
                        expire=expire, play_kwargs=play_kwargs)

    def remove_slide(self, slide, transition_config=None):
        # Note that you can't remove the last slide, so if you try it will
        # create a new slide called "blank" which is a blank slide and priority
        # 0 and show that instead

        # slide can be slide name or slide obj

        # todo
        # Warning, if you just created a slide, you have to wait at least on
        # tick before removing it. Can we prevent that? What if someone tilts
        # at the exact perfect instant when a mode was starting or something?

        # maybe we make sure to run a kivy tick between bcp reads or something?

        try:
            slide = self.get_screen(slide)
        except ScreenManagerException:  # no slide by that name
            if not isinstance(slide, Slide):
                return

        slide.prepare_for_removal()

        self.mc.active_slides.pop(slide.name, None)

        # If the current slide is the active one, find the next highest
        # priority one to show instead.
        if self.current_screen == slide:
            new_slide = self.get_next_highest_slide(slide)

            if transition_config:
                self.transition = self.mc.transition_manager.get_transition(
                    transition_config)
            elif self.current_screen.transition_out:
                self.transition = self.mc.transition_manager.get_transition(
                    self.current_screen.transition_out)
            else:
                self.transition = NoTransition()

            self._set_current_slide(new_slide)

        try:
            self.remove_widget(slide)
        except WidgetException:
            pass

    def _set_current_slide(self, slide):
        # slide frame requires at least one slide, so if you try to set current
        # to None, it will create a new slide called '<display name>_blank' at
        # priority 0 and show that one

        # I think there's a bug in Kivy 1.9.1. According to the docs, you
        # should be able to set self.current to a screen name. But if that
        # screen is already managed by this screen manager, it will raise
        # an exception, and the source is way deep in their code and not
        # easy to fix by subclassing. So this is sort of a hack that looks
        # for that exception, and if it sees it, it just removes and
        # re-adds the screen.
        if not slide:
            slide = self.add_slide(name='{}_blank'.format(self.name),
                                   priority=0, key=None)

        if self.current == slide.name:
            return

        try:
            self.current = slide.name
        except WidgetException:
            self.remove_widget(slide)
            self.add_widget(slide)
            self.current = slide.name

        # Post the event via callback at the end of the frame in case more than
        # one slide was set in this frame, so we only want to post the event
        # for the slide that actually became active.

        if not self._flag_slide_changed:  # only call this once per frame
            self.mc.clock.schedule_once(self._post_active_slide_event, -1)
            self._flag_slide_changed = True

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

    def add_widget_to_frame(self, widget):
        self.parent.parent.add_widget(widget)

    def add_widgets_to_frame(self, widgets):
        for w in widgets:
            self.add_widget_to_frame(w)

    def remove_widgets_by_key(self, key):
        for widget in self.get_widgets_by_key(key):
            self.parent.parent.remove_widget(widget)

    def get_widgets_by_key(self, key):
        try:
            return [x for x in self.parent.children if x.key == key]
        except AttributeError:
            return []

    def _post_active_slide_event(self, dt):
        del dt

        self._flag_slide_changed = False

        self.mc.post_mc_native_event('slide_{}_active'.format(self.current))
        """event: slide_(name)_active

        desc: A slide called (name) has just become active, meaning that
        it's now showing as the current slide.

        This is useful for things like the widget_player where you want to
        target a widget for a specific slide, but you can only do so if
        that slide exists.

        Slide names do not take into account what display or slide frame
        they're playing on, so be sure to create machine-wide unique names
        when you're naming your slides.
        """
