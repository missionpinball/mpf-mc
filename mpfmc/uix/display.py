"""Contains the Display base class, which is a logical display in the mpf-mc."""
from typing import List, Union, Optional
from math import floor

from kivy.uix.floatlayout import FloatLayout

from kivy.clock import Clock
from kivy.uix.screenmanager import (ScreenManager, NoTransition,
                                    SlideTransition, SwapTransition,
                                    FadeTransition, WipeTransition,
                                    FallOutTransition, RiseInTransition,
                                    ScreenManagerException)
from kivy.uix.widget import WidgetException as KivyWidgetException
from kivy.uix.scatter import Scatter
from kivy.graphics import (
    Translate, Fbo, ClearColor, ClearBuffers, Scale)
from kivy.properties import ObjectProperty

from mpfmc.uix.widget import Widget
from mpfmc.uix.slide import Slide


MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc                 # pylint: disable-msg=cyclic-import,unused-import
    from kivy.uix.widget import \
        Widget as KivyWidget                        # pylint: disable-msg=cyclic-import,unused-import,ungrouped-imports
    from mpfmc.uix.widget import WidgetContainer    # pylint: disable-msg=cyclic-import,unused-import,ungrouped-imports


transition_map = dict(none=NoTransition,
                      slide=SlideTransition,
                      swap=SwapTransition,
                      fade=FadeTransition,
                      wipe=WipeTransition,
                      fall_out=FallOutTransition,
                      rise_in=RiseInTransition)


# pylint: disable-msg=too-many-instance-attributes
class Display(ScreenManager):

    """A display which can be used to show slides."""

    displays_to_initialize = 0

    texture = ObjectProperty(None, allownone=True)

    @staticmethod
    def create_default_display(mc: "MpfMc") -> None:
        """Create default display."""
        Display(mc, 'default', width=800, height=600, enabled=True)

    def __init__(self, mc: "MpfMc", name: str, **kwargs) -> None:
        """Initialise Display."""
        self.mc = mc
        self.name = name
        self.config = kwargs
        self._ready = False
        self.tags = []
        self.display = self
        self.parents = []
        self.mc.track_leak_reference(self)

        Display.displays_to_initialize += 1

        self.native_size = (self.config['width'], self.config['height'])
        self.size_hint = (None, None)
        self.size = self.native_size
        self.enabled = self.config['enabled']

        self.transition = NoTransition()

        self._blank_slide_name = '{}_blank'.format(self.name)

        super().__init__()

        # It is possible that the current slide changes more than one time during a single clock
        # frame. Sending multiple slide active events is not desired in this situation. This can
        # easily be solved using Kivy clock events. The clock event will only be triggered once
        # per clock frame no matter how many times it is called.
        self._current_slide_changed = Clock.create_trigger(self._post_active_slide_event, -1)

        # Need to create a widget that will be the parent of the slide manager.  This is
        # necessary to allow widgets with negative z values to remain in the display while
        # slides are changed.
        self.container = FloatLayout(size_hint=(None, None), size=self.size)
        self.container.z = 0
        self.container.add_widget(self)

        self._display_created()

    def __repr__(self):
        return '<Display name={}{}, current slide={}, total slides={}>'.format(
            self.name, self.size, self.current_slide_name, len(self.slides))

    def get_frame_data(self, *args):
        """Return the content of this display as buffer.

        @see: widget.export_to_png
        """
        del args

        fbo = Fbo(size=self._slide_manager_parent.size, with_stencilbuffer=True)

        with fbo:
            ClearColor(0, 0, 0, 1)
            ClearBuffers()
            Scale(1, -1, 1)
            Translate(-self.x,
                      -self.y - self.height, 0)

        fbo.add(self.canvas)
        fbo.draw()
        data = fbo.texture.pixels
        fbo.remove(self.canvas)

        return data

    @property
    def ready(self):
        """Return true if display is ready."""
        return self._ready

    @property
    def parent_widgets(self) -> List["WidgetContainer"]:
        """The list of all widgets owned by the display parent."""
        return [x for x in self.container.children if x != self]

    def has_parent(self) -> bool:
        """Returns whether or not the display has a parent."""
        return bool(self.container.parent is not None)

    def _display_created(self, *args) -> None:
        """Callback after this display is created."""
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
        # Add this display to the list of all available displays
        self.mc.displays[self.name] = self

        # If this display is configured as the default, set it.
        # If this display would overwrite an existing default, raise an AssertionError.
        try:
            if self.config['default']:
                if 'default' not in self.mc.targets:
                    self.mc.targets['default'] = self
                else:
                    raise AssertionError('Multiple displays have been set as the default. Please choose a single \
                        display to default to (\"{}\" is currently set as the default).'.format(
                        self.mc.targets['default'].name))
        except KeyError:
            pass

        # Initialization is just about done, schedule callback to finish
        Clock.schedule_once(self._init_done, 0)

    def _init_done(self, *args) -> None:
        """Callback after this display has been initialized."""
        del args
        self.mc.post_mc_native_event('display_{}_initialized'.format(self.name))
        '''event: display_(name)_initialized
        config_section: displays
        class_label: display

        desc: The display called (name) has been initialized. This event is
        generated in the MC, so it won't be sent to MPF if the MC is started up
        and ready first.

        This event is part of the MPF-MC boot process and is not particularly
        useful for game developers. If you want to show a "boot" slide as
        early as possible, use the *mc_ready* event.
        '''

        Display.displays_to_initialize -= 1

        # Callback function to set this display to ready state once all displays
        # have been initialized
        self.mc.events.add_handler('displays_initialized', self._finalize_setup, priority=10000)

        if not Display.displays_to_initialize:
            Clock.schedule_once(self._displays_initialized)

    def _displays_initialized(self, *args) -> None:
        """Callback after all displays have been initialized."""
        del args

        # Determine the 'default' display
        if len(self.mc.displays) == 1:
            self.mc.targets['default'] = next(iter(self.mc.displays.values()))

        elif 'default' not in self.mc.targets:
            for target in ('window', 'dmd'):
                if target in self.mc.displays:
                    self.mc.targets['default'] = self.mc.displays[target]
                    break

            if 'default' not in self.mc.targets:
                self.mc.targets['default'] = self.mc.displays[
                    (sorted(self.mc.displays.keys()))[0]]

        self.mc.log.info("Display: Setting '%s' as default display", self.mc.targets['default'].name)

        self.mc.displays_initialized()

    def _finalize_setup(self, **kwargs) -> None:
        """Callback function after all displays have been initialized.  This
        method finalizes the display setup and gets it ready to use as a
        target. The 'display_{}_ready' event is posted once it is ready.
        """
        del kwargs

        # This display is now a valid target so add it to the list
        self.mc.targets[self.name] = self

        # Create a blank slide for this display. Why?
        # 1. sometimes people try to play widgets with no slide. This makes
        # that work.
        # 2. the first slide that's created and added to this frame will be
        # automatically shown, which we don't want. Also we want to ensure that
        # our slide event will be called which only happens when this slide is
        # switched to, rather than automatically added.
        self.create_blank_slide()

        self._ready = True

        self.mc.post_mc_native_event('display_{}_ready'.format(self.name))
        '''event: display_(name)_ready
        config_section: displays
        class_label: display

        desc: The display target called (name) is now ready and available to
        show slides.
        This event is useful with display widgets where you want to add
        a display to an existing slide which shows some content, but you
        need to make sure the display exists before showing a slide.
        So if you have a display called "overlay", then you can add it to
        a slide however you want, and when it's added, the event
        "display_overlay_ready" will be posted, and then you can use that event
        in your slide_player to trigger the first slide you want to show.
        Note that this event is posted by MPF-MC and will not exist on the MPF
        side. So you can use this event for slide_player, widget_player, etc.,
        but not to start shows or other things controlled by MPF.'''

    @property
    def current_slide(self) -> "Slide":
        """Returns the Slide object of the current slide."""
        return self.current_screen

    @current_slide.setter
    def current_slide(self, value: Union[str, "Slide"]):
        """Set the current slide.
        You can set it to a Slide object or a string of the slide name.
        """
        if isinstance(value, Slide):
            self._set_current_slide(value)
        elif isinstance(value, str):
            self._set_current_slide_name(value)

    @property
    def current_slide_name(self) -> str:
        """Returns the string name of the current slide."""
        return self.current

    @current_slide_name.setter
    def current_slide_name(self, value: str):
        """Sets the current slide based on the string name of the slide you
        want to be shown."""
        self._set_current_slide_name(value)

    @property
    def slides(self) -> List["Slide"]:
        """Return list of slide objects of all the active slides for this slide frame."""
        return self.screens

    def create_blank_slide(self) -> "Slide":
        """Creates the blank slide for this display."""
        return self.add_slide(self._blank_slide_name)

    def get_slide(self, name: str) -> "Slide":
        """Return the Slide associated with the name or raise a
        :class:`ScreenManagerException` if not found."""
        return self.get_screen(name)

    # pylint: disable-msg=too-many-arguments
    def add_slide(self, name: str, config: Optional[dict] = None, priority: int = 0,
                  key: Optional[str] = None, play_kwargs: Optional[dict] = None) -> "Slide":
        """Add a slide to this display.

        Add a slide to the list of slides managed by the display (or returns the existing
        slide with the specified name if it already exists).  This method just adds the
        slide.  It does not display it.

        Args:
            name: The slide name.
            config: The slide config.
            priority: The slide priority.
            key: Optional key.
            play_kwargs: Additional play kwargs.

        Returns:
            The Slide object.
        """
        # See if slide already exists.  If so, return it
        if self.has_screen(name):
            return self.get_screen(name)

        # Slide() creates a new slide and adds it to this screen manager (display)
        return Slide(mc=self.mc, name=name, target=self.name,
                     config=config, key=key, priority=priority,
                     play_kwargs=play_kwargs)

    # pylint: disable-msg=too-many-arguments
    def show_slide(self, slide_name: str, transition: Optional[str] = None,
                   key: Optional[str] = None, force: bool = False, priority: int = 0,
                   show: Optional[bool] = True, expire: Optional[float] = None,
                   play_kwargs: Optional[dict] = None, **kwargs) -> bool:
        """
        Request to show the specified slide. Many of the slide parameters may be overridden
        using the arguments for this function.

        Args:
            slide_name: The name of the slide.
            transition: The slide transition (overrides any stored in the slide).
            key: The slide key.
            force: When true, the slide will be displayed regardless of the priority of the
                current slide.
            priority: The priority of the slide to show.
            show: Whether or not to actually show the slide.
            expire: Expiration time (in seconds) after which the slide will be automatically
                removed (overrides value stored in the slide).
            play_kwargs: Kwargs related to playing/displaying the slide.
            **kwargs: Additional kwargs (will override settings in the play_kwargs parameter).

        Returns:
            True is the slide will be shown, False otherwise.
        """
        # TODO: Is the show parameter really needed?  Why call show_slide and not show the slide?
        if not play_kwargs:
            play_kwargs = kwargs
        else:
            play_kwargs.update(kwargs)

        if self.has_screen(slide_name):
            slide = self.get_screen(slide_name)
        else:
            try:
                slide_config = self.mc.slides[slide_name]
            except KeyError:
                raise AssertionError("Slide {} not found".format(slide_name))
            slide = self.add_slide(name=slide_name,
                                   config=slide_config,
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
            self.transition.stop()
            self.transition = self.mc.transition_manager.get_transition(transition)

            self._set_current_slide(slide)
            return True

        else:
            # Not showing this slide
            return False

    # pylint: disable-msg=too-many-arguments
    def add_and_show_slide(self, widgets: Optional[dict] = None,
                           slide_name: Optional[str] = None,
                           transition: Optional[str] = None, priority: int = 0,
                           key: Optional[str] = None, force: bool = False,
                           background_color=None,
                           expire: Optional[float] = None, play_kwargs=None,
                           **kwargs) -> bool:
        """Create and show the slide.

        If a slide with this name already exists, it will be replaced.

        Args:
            widgets: An optional dictionary of widgets to add to the slide.
            slide_name: The name of the slide.
            transition: The slide transition (overrides any stored in the slide).
            force: When true, the slide will be displayed regardless of the priority of the
                current slide.
            key: The slide key.
            priority: The priority of the slide to show.
            expire: Expiration time (in seconds) after which the slide will be automatically
                removed (overrides value stored in the slide).
            play_kwargs: Kwargs related to playing/displaying the slide.
            **kwargs: Additional kwargs (will override settings in the play_kwargs parameter).

        Returns:
            True is the slide will be shown, False otherwise.
        """
        if not play_kwargs:
            play_kwargs = kwargs
        else:
            play_kwargs.update(kwargs)

        slide_obj = self.add_slide(name=slide_name,
                                   config=dict(widgets=widgets, background_color=background_color),
                                   priority=priority, key=key)

        return self.show_slide(slide_name=slide_obj.name, transition=transition,
                               priority=priority, force=force, key=key,
                               expire=expire, play_kwargs=play_kwargs)

    def remove_slide(self, slide: Union["Slide", str],
                     transition_config: Optional[dict] = None) -> bool:
        """Remove a slide from the display.

        Args:
            slide: The slide to remove (can be name string or Slide object)
            transition_config: Optional dictionary containing the transition configuration
                to use while removing the slide (overrides slide setting).

        Returns:
            True if the slide is scheduled to be removed, False otherwise

        Notes:
            You can't remove the automatically generated blank slide, so if you try it will
            raise an exception.
        """
        # TODO:
        # Warning, if you just created a slide, you have to wait at least on
        # tick before removing it. Can we prevent that? What if someone tilts
        # at the exact perfect instant when a mode was starting or something?

        # maybe we make sure to run a Kivy tick between bcp reads or something?
        try:
            slide = self.get_slide(slide)
        except ScreenManagerException:  # no slide by that name
            if not isinstance(slide, Slide):
                return False

        # Do not allow the blank slide to be removed
        if slide.name == self._blank_slide_name:
            return False

        slide.prepare_for_removal()

        self.mc.active_slides.pop(slide.name, None)

        # If the current slide is the active one, find the next highest
        # priority one to show instead.
        if self.current_slide == slide:
            new_slide = self._get_next_highest_priority_slide(slide)
            if self.transition:
                self.transition.stop()

            if transition_config:
                self.transition = self.mc.transition_manager.get_transition(
                    transition_config)
            elif self.current_slide.transition_out:
                self.transition = self.mc.transition_manager.get_transition(
                    self.current_slide.transition_out)
            else:
                self.transition = NoTransition()

            self.transition.bind(on_complete=self._remove_transition)
        else:
            new_slide = None

        # Set the new slide first, so we can transition out of the old before removing
        if new_slide:
            self._set_current_slide(new_slide)
        try:
            self.remove_widget(slide)
        except ScreenManagerException:
            return False

        return True

    def _remove_transition(self, transition):
        """Remove transition if done."""
        if self.transition == transition:
            self.transition = NoTransition()

    def _set_current_slide(self, slide: "Slide"):
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
            slide = self.create_blank_slide()

        if self.current == slide.name:
            return

        try:
            self.current = slide.name
        except KivyWidgetException:
            self.remove_widget(slide)
            self.add_widget(slide)
            self.current = slide.name

        # Post the event via callback at the end of the frame in case more than
        # one slide was set in this frame, so we only want to post the event
        # for the slide that actually became active.  The Kivy clock event will
        # only call the associated callback once per frame when triggered no
        # matter how many times it is called.
        self._current_slide_changed()

    def _set_current_slide_name(self, slide_name):
        try:
            self._set_current_slide(self.get_screen(slide_name))
        except ScreenManagerException:
            raise ValueError('Cannot set current slide to "{}" as there is '
                             'no slide in this slide_frame with that '
                             'name'.format(slide_name))

    def _get_next_highest_priority_slide(self, slide: "Slide") -> "Slide":
        """Return the slide with the next highest priority."""
        new_slide = None

        for s in self.slides:
            if s == slide:
                continue
            if not new_slide:
                new_slide = s
            elif s.priority > new_slide.priority:
                new_slide = s
            elif (s.priority == new_slide.priority and
                    s.creation_order > new_slide.creation_order):
                new_slide = s

        return new_slide

    def add_widget_to_current_slide(self, widget: "KivyWidget"):
        """Adds the widget to the current slide."""
        self.current_slide.add_widget(widget)

    def add_widgets_to_current_slide(self, widgets: List["KivyWidget"]):
        """Adds a list of widgets to the current slide."""
        for w in widgets:
            self.add_widget_to_current_slide(w)

    def remove_widgets_by_key(self, key: str) -> None:
        """Removes all widgets with the specified key."""
        for widget in self.find_widgets_by_key(key):
            widget.prepare_for_removal()
            if isinstance(widget, Widget) and widget.container and widget.container.parent:
                widget.container.parent.remove_widget(widget.container)
            elif widget.parent:
                widget.parent.remove_widget(widget)

    def find_widgets_by_key(self, key: str) -> List["KivyWidget"]:
        """Retrieves a list of all widgets with the specified key value."""
        widgets = []

        # First find all matching widgets owned by the slide parent
        for child in self.parent_widgets:
            widgets.extend([x for x in child.walk(restrict=True, loopback=False)
                            if hasattr(x, "key") and x.key == key])

        # Finally find all matching widgets owned by each slide
        for slide in self.slides:
            widgets.extend(slide.find_widgets_by_key(key))

        return widgets

    def _post_active_slide_event(self, dt) -> None:
        """Posts an event that a new slide is now active."""
        del dt

        self.mc.post_mc_native_event('slide_{}_active'.format(self.current_slide_name))
        """event: slide_(name)_active
        config_section: slides
        class_label: slide

        desc: A slide called (name) has just become active, meaning that
        it's now showing as the current slide.
        This is useful for things like the widget_player where you want to
        target a widget for a specific slide, but you can only do so if
        that slide exists.
        Slide names do not take into account what display they're playing on,
        so be sure to create machine-wide unique names when you're naming
        your slides.
        """


class DisplayOutput(Scatter):

    """Show a display as a widget."""

    def __init__(self, parent: "KivyWidget", display: "Display", **kwargs):
        kwargs.setdefault('do_scale', False)
        kwargs.setdefault('do_translation', False)
        kwargs.setdefault('do_rotation', False)

        super().__init__(**kwargs)

        self.key = None

        # It is important that the content of this display output does not contain any
        # circular references to the same display (cannot do a recursive
        # picture-in-picture or Kivy will crash).  Detect and prevent that situation.

        # Rather than adding the display as a child of this widget, we will simply
        # add the display's canvas to this widget's canvas.  This allows the display
        # to essentially have multiple parents. The canvas contains all the
        # instructions needed to draw the widgets.
        self.display = display

        parent.bind(size=self.on_parent_resize)
        self._fit_to_parent()

    #
    # Tree management
    #
    def add_display_source(self, widget):
        """Add a new widget as a child of this widget.

        :Parameters:
            `widget`: :class:`Widget`
                Widget to add to our list of children.
        """
        if not isinstance(widget, Display):
            raise KivyWidgetException(
                'add_widget_multi_parent() can be used only with instances'
                ' of the Display class.')

        widget = widget.__self__
        if widget is self:
            raise KivyWidgetException(
                'Widget instances cannot be added to themselves.')

        widget.parent = self
        widget.parents.append(self)

        canvas = self.canvas
        canvas.add(widget.container.canvas)

    def remove_display_source(self, widget):
        """Remove a display."""
        if not isinstance(widget, Display):
            raise KivyWidgetException(
                'remove_display_source() can be used only with instances'
                ' of the Display class.')
        widget.parents.remove(self)
        widget.parent = None
        self.canvas.remove(widget.container.canvas)

    def __repr__(self) -> str:  # pragma: no cover
        try:
            return '<DisplayOutput size={}, pos={}, source={}>'.format(
                self.size, self.pos, self.display.name)
        except AttributeError:
            return '<DisplayOutput size={}, source=(none)>'.format(self.size)

    def on_parent_resize(self, *args):
        """Fit to parent on resize."""
        del args
        self._fit_to_parent()

    def _fit_to_parent(self, *args):
        """Center and scale display output in parent display widget"""
        del args
        if self.parent:
            self.scale = min(self.parent.width / float(self.display.width),
                             self.parent.height / float(self.display.height))
            self.width = floor(self.scale * self.display.width)
            self.height = floor(self.scale * self.display.height)
            self.x = (self.parent.width - self.width) // 2
            self.y = (self.parent.height - self.height) // 2
