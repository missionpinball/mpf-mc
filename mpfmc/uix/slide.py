"""A slide which can show widgets."""
from bisect import bisect
from typing import List, Optional

from kivy.graphics.vertex_instructions import Rectangle
from kivy.uix.screenmanager import Screen
from kivy.uix.stencilview import StencilView
from kivy.graphics import Color
from kivy.properties import ListProperty, AliasProperty

from mpfmc.uix.widget import Widget, create_widget_objects_from_config

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc                 # pylint: disable-msg=cyclic-import,unused-import
    from kivy.uix.widget import \
        Widget as KivyWidget                        # pylint: disable-msg=cyclic-import,unused-import,ungrouped-imports
    from mpfmc.uix.widget import WidgetContainer    # pylint: disable-msg=cyclic-import,unused-import,ungrouped-imports


# pylint: disable-msg=too-many-instance-attributes
class Slide(Screen, StencilView):

    """A slide on a display."""

    next_id = 0

    @classmethod
    def get_next_id(cls) -> int:
        """Return the next slide id."""
        Slide.next_id += 1
        return Slide.next_id

    # pylint: disable-msg=too-many-arguments
    def __init__(self, mc: "MpfMc", name: Optional[str], config: Optional[dict] = None,
                 target: str = 'default', key: Optional[str] = None,
                 priority: int = 0, play_kwargs: Optional[dict] = None) -> None:
        """initialize slide."""
        # config is a dict. widgets will be in a key
        # assumes config, if present, is validated.
        self.creation_order = Slide.get_next_id()

        if not name:
            name = 'Anon_{}'.format(self.creation_order)

        self.mc = mc
        self.name = name
        self.priority = priority
        self.pending_widgets = set()
        self.key = key
        self.mc.track_leak_reference(self)

        if not config:
            config = self.mc.config_validator.validate_config('slides', dict())

        self.transition_out = config.get('transition_out', None)
        self.expire = config.get('expire', None)

        self.display = self.mc.targets[target]

        self.size_hint = (None, None)
        super().__init__()
        self.size = self.display.native_size
        self.orig_w, self.orig_h = self.size
        self.z = 0

        if 'widgets' in config:  # don't want try, swallows too much
            widgets = create_widget_objects_from_config(
                mc=self.mc,
                config=config['widgets'], key=self.key,
                play_kwargs=play_kwargs)

            self.add_widgets(widgets)

        self.display.add_widget(self)
        self.mc.active_slides[name] = self
        self.mc.slides[name] = config

        self.background_color = config.get('background_color', [0.0, 0.0, 0.0, 1.0])
        if self.background_color != [0.0, 0.0, 0.0, 0.0]:
            with self.canvas.before:    # noqa
                Color(*self.background_color)
                Rectangle(size=self.size, pos=(0, 0))

        self.opacity = config.get('opacity', 1.0)

        self.mc.post_mc_native_event(
            'slide_{}_created'.format(self.name))

        """event: slide_(name)_created
        config_section: slides
        class_label: slide

        desc: A slide called (name) has just been created.

        This means that this slide now exists, but it's not necessarily the
        active (showing) slide, depending on the priorities of the other slides
        and/or what else is going on.

        This is useful for things like the widget_player where you want to
        target a widget for a specific slide, but you can only do so if
        that slide exists.

        Slide names do not take into account what display or slide frame
        they're playing on, so be sure to create machine-wide unique names
        when you're naming your slides.

        """

    def __repr__(self):
        return '<Slide name={}, priority={}, id={}>'.format(self.name,
                                                            self.priority,
                                                            self.creation_order)

    def add_widgets_from_library(self, name: str, key: Optional[str] = None,
                                 widget_settings: Optional[dict] = None,
                                 play_kwargs: Optional[dict] = None,
                                 **kwargs) -> List["Widget"]:
        """Add a widget to the slide by name from the library of pre-defined widgets.

        Args:
            name: The name of the widget to add.
            key: An optional key.
            widget_settings: An optional dictionary of widget settings to override those in
                the library.
            play_kwargs: An optional dictionary of play settings to override those in
                the library.
            **kwargs:  Additional arguments.

        Returns:
            A list of widgets (MpfWidget objects) added to the slide.
        """
        del kwargs

        if name not in self.mc.widgets:
            raise ValueError("Widget {} not found".format(name))

        widgets_added = create_widget_objects_from_config(config=self.mc.widgets[name],
                                                          mc=self.mc,
                                                          key=key,
                                                          widget_settings=widget_settings,
                                                          play_kwargs=play_kwargs)
        for widget in widgets_added:
            self.add_widget(widget)

        return widgets_added

    def add_widgets(self, widgets: List["Widget"]):
        """Adds a list of widgets to this slide."""
        for w in widgets:
            self.add_widget(w)

    # pylint: disable-msg=arguments-differ
    def add_widget(self, widget: "Widget", **kwargs) -> None:
        """Add a widget to this slide.

        Args:
            widget: An MPF-enhanced widget (which will include details like z
                order and removal keys.)

        Notes:
            Widgets are drawn in order from the end of the children list to the
            beginning, meaning the first item in the child list is draw last so
            it will appear on top of all other items.

            This method respects the z-order of the widget it's adding and inserts
            it into the proper position in the widget tree. Higher numbered z order
            values will be inserted after (so they draw on top) of existing ones.

            If the new widget has the same priority of existing widgets, the new
            one is inserted after the widgets of that priority, to maintain the
            drawing order of the configuration file.
        """
        del kwargs
        if widget.get_display() == self.display:
            raise AssertionError("Cannot add widget {} to display {} because the widget uses the same display.".
                                 format(widget, self.display))

        if widget.z < 0:
            self.add_widget_to_parent_frame(widget)
            return

        # Insert the widget in the proper position in the z-order
        super().add_widget(widget, bisect(self.children, widget))

    def remove_widgets_by_key(self, key: str) -> None:
        """Removes all widgets from this slide with the specified key value."""
        for widget in self.find_widgets_by_key(key):
            if isinstance(widget, Widget):
                widget.remove()
            else:
                self.remove_widget(widget)

    def find_widgets_by_key(self, key: str) -> List["Widget"]:
        """Return a list of widgets with the matching key value by searching
        the tree of children belonging to this slide."""
        return [w for child in self.children
                for w in child.walk(restrict=True, loopback=False) if hasattr(w, "key") and w.key == key]

    def add_widget_to_parent_frame(self, widget: "KivyWidget"):
        """Adds this widget to this slide's parent instead of to this slide.

        Args:
            widget:
                The widget object.

        Notes:
            Widgets added to the parent slide_frame stay active and visible even
            if the slide in the frame changes.
        """
        # TODO: Determine proper z-order for negative z-order values
        self.manager.container.add_widget(widget)

    def schedule_removal(self, secs: float) -> None:
        """Schedules the removal of this slide after the specified number of seconds elapse."""
        self.mc.clock.schedule_once(self.remove, secs)

    def remove(self, dt=None) -> None:
        """Removes the slide from the parent display."""
        del dt

        try:
            self.manager.remove_slide(slide=self,
                                      transition_config=self.transition_out)

        except AttributeError:
            # looks like slide was already removed, but let's clean it up just
            # in case
            self.prepare_for_removal()
            self.mc.active_slides.pop(self.name, None)

    def prepare_for_removal(self) -> None:
        """Performs housekeeping chores just prior to a slide being removed."""
        self.mc.clock.unschedule(self.remove)

        for widget in self.children:
            if hasattr(widget, 'prepare_for_removal'):  # try swallows too much
                widget.prepare_for_removal()

        self.mc.post_mc_native_event('slide_{}_removed'.format(self.name))

        """event: slide_(name)_removed
        config_section: slides
        class_label: slide

        desc: A slide called (name) has just been removed.

        This event is posted whenever a slide is removed, regardless of
        whether or not that slide was active (showing).

        Note that even though this event is called "removed", it's actually
        posted as part of the removal process. (e.g. there are still some
        clean-up things that happen afterwards.)

        Slide names do not take into account what display or slide frame
        they're playing on, so be sure to create machine-wide unique names
        when you're naming your slides.

        """

    def on_pre_enter(self, *args):
        del args
        for widget in self.children:
            widget.on_pre_show_slide()

    def on_enter(self, *args):
        del args
        for widget in self.children:
            widget.on_show_slide()

    def on_pre_leave(self, *args):
        del args
        for widget in self.children:
            widget.on_pre_slide_leave()

    def on_leave(self, *args):
        del args
        for widget in self.children:
            widget.on_slide_leave()

    def on_slide_play(self):
        for widget in self.children:
            widget.on_slide_play()

    #
    # Properties
    #

    background_color = ListProperty([0.0, 0.0, 0.0, 1.0])
    '''The background color of the slide, in the (r, g, b, a)
    format.

    :attr:`background_color` is a :class:`~kivy.properties.ListProperty` and
    defaults to [0, 0, 0, 1.0].
    '''

    def _get_parent_widgets(self) -> List["WidgetContainer"]:
        """Return the current list of widgets owned by the slide manager parent."""
        return [x for x in self.manager.parent.children if x != self.manager]

    parent_widgets = AliasProperty(_get_parent_widgets, None)
    '''List of all the :class:`MpfWidget` widgets that belong to the slide
    manager of this slide (read-only).  You should not change this list
    manually. Use the :meth:`add_widget <mpfmc.uix.widget.MpfWidget.add_widget>`
    method instead.

    Use this property rather than the 'self.manager.parent.children' property in
    case the slide architecture changes in the future.
    '''

    def _get_widgets(self) -> List["WidgetContainer"]:
        """Returns the current list of widget children owned by this slide."""
        return self.children

    widgets = AliasProperty(_get_widgets, None, bind=('children', ))
    '''List of all the :class:`MpfWidget` children widgets of this slide (read-only).
    You should not change this list manually. Use the
    :meth:`add_widget <mpfmc.uix.widget.MpfWidget.add_widget>` method instead.

    Use this property rather than the 'children' property in case the slide
    architecture changes in the future.
    '''
