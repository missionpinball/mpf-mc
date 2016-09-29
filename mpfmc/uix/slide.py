from bisect import bisect

from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import Rectangle
from kivy.uix.screenmanager import Screen
from kivy.uix.stencilview import StencilView

from mpfmc.core.utils import set_position
from mpfmc.uix.widget import create_widget_objects_from_config


class Slide(Screen):
    next_id = 0

    @classmethod
    def get_id(cls):
        Slide.next_id += 1
        return Slide.next_id

    # pylint: disable-msg=too-many-arguments
    def __init__(self, mc, name, config=None, target='default', key=None,
                 priority=0, play_kwargs=None):

        # config is a dict. widgets will be in a key
        # assumes config, if present, is validated.

        self.creation_order = Slide.get_id()

        if not name:
            name = 'Anon_{}'.format(self.creation_order)

        self.mc = mc
        self.name = name
        self.priority = priority
        self.pending_widgets = set()
        self.key = key

        if not config:
            config = self.mc.config_validator.validate_config('slides', dict())

        self.transition_out = config.get('transition_out', None)
        self.expire = config.get('expire', None)

        target = mc.targets[target]

        self.size_hint = (None, None)
        super().__init__()
        self.size = target.native_size
        self.orig_w, self.orig_h = self.size

        self.stencil = StencilView(size_hint=(None, None),
                                   size=self.size)
        self.stencil.config = dict()
        self.stencil.config['z'] = 0
        super().add_widget(self.stencil)

        if 'widgets' in config:  # don't want try, swallows too much

            widgets = create_widget_objects_from_config(
                mc=self.mc,
                config=config['widgets'], key=self.key,
                play_kwargs=play_kwargs)

            self.add_widgets(widgets)

        self.mc.active_slides[name] = self
        target.add_widget(self)
        self.mc.slides[name] = config

        bg = config.get('background_color', [0.0, 0.0, 0.0, 1.0])
        if bg != [0.0, 0.0, 0.0, 0.0]:
            with self.canvas.before:
                Color(*bg)
                Rectangle(size=self.size, pos=(0, 0))

        self.opacity = config.get('opacity', 1.0)

        self.mc.post_mc_native_event(
            'slide_{}_created'.format(self.name))

        """event: slide_(name)_created

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
            self.priority, self.creation_order)

    def add_widgets_from_library(self, name, key=None, widget_settings=None, play_kwargs=None,
                                 **kwargs):
        if name not in self.mc.widgets:
            raise ValueError("Widget %s not found", name)

        return self.add_widgets_from_config(config=self.mc.widgets[name],
                                            key=key,
                                            widget_settings=widget_settings,
                                            play_kwargs=play_kwargs)

    def add_widgets_from_config(self, config, key=None, play_kwargs=None,
                                widget_settings=None):

        if not isinstance(config, list):
            config = [config]
        widgets_added = list()

        if not play_kwargs:
            play_kwargs = dict()  # todo

        for widget in config:

            if widget_settings:
                widget_settings = self.mc.config_validator.validate_config(
                    'widgets:{}'.format(widget['type']), widget_settings,
                    base_spec='widgets:common', add_missing_keys=False)

                widget.update(widget_settings)

            configured_key = widget.get('key', None)

            if (configured_key and key and "." not in key and
                    configured_key != key):
                raise KeyError("Widget has incoming key '{}' which does not "
                               "match the key in the widget's config "
                               "'{}'.".format(key, configured_key))

            if configured_key:
                this_key = configured_key
            else:
                this_key = key

            widget_obj = self.mc.widgets.type_map[widget['type']](
                mc=self.mc, config=widget, slide=self, key=this_key, play_kwargs=play_kwargs)

            top_widget = widget_obj

            # some widgets (like slide frames) have parents, so we need to make
            # sure that we add the parent widget to the slide
            while top_widget.parent:
                top_widget = top_widget.parent

            self.add_widget(top_widget)

            widget_obj.pos = set_position(self.width,
                                          self.height,
                                          widget_obj.width,
                                          widget_obj.height,
                                          widget_obj.config['x'],
                                          widget_obj.config['y'],
                                          widget_obj.config['anchor_x'],
                                          widget_obj.config['anchor_y'],
                                          widget_obj.config['adjust_top'],
                                          widget_obj.config['adjust_right'],
                                          widget_obj.config['adjust_bottom'],
                                          widget_obj.config['adjust_left'])
            widgets_added.append(widget_obj)

        return widgets_added

    def add_widgets(self, widgets):
        for w in widgets:
            self.add_widget(w)

    def add_widget(self, widget, **kwargs):
        """Adds a widget to this slide.

        Args:
            widget: An MPF-enhanced widget (which will include details like z
                order and removal keys.)

        This method respects the z-order of the widget it's adding and inserts
        it into the proper position in the widget tree. Higher numbered z order
        values will be inserted after (so they draw on top) of existing ones.

        If the new widget has the same priority of existing widgets, the new
        one is inserted after the widgets of that priority, meaning the newest
        widget will be displayed on top of existing ones with the same
        priority.

        """
        del kwargs

        if widget.config['z'] < 0:
            self.add_widget_to_parent_frame(widget)
            return

        self.stencil.add_widget(widget, bisect(self.stencil.children, widget))

        widget.pos = set_position(self.size[0],
                                  self.size[1],
                                  widget.width,
                                  widget.height,
                                  widget.config['x'],
                                  widget.config['y'],
                                  widget.config['anchor_x'],
                                  widget.config['anchor_y'],
                                  widget.config['adjust_top'],
                                  widget.config['adjust_right'],
                                  widget.config['adjust_bottom'],
                                  widget.config['adjust_left'])

    def remove_widgets_by_key(self, key):
        for widget in self.get_widgets_by_key(key):
            self.stencil.remove_widget(widget)

    def get_widgets_by_key(self, key):
        return [x for x in self.stencil.children if x.key == key]

    def remove_widget(self, widget):
        self.stencil.remove_widget(widget)

    def add_widget_to_parent_frame(self, widget):
        """Adds this widget to this slide's parent frame instead of to this
        slide.

        Args:
            widget:
                The widget object.

        Widgets added to the parent slide_frame stay active and visible even
        if the slide in the frame changes.

        """
        self.manager.parent.parent.add_widget(widget)

    def schedule_removal(self, secs):
        self.mc.clock.schedule_once(self.remove, secs)

    def remove(self, dt=None):
        del dt

        try:
            self.manager.remove_slide(slide=self,
                                      transition_config=self.transition_out)

        except AttributeError:
            # looks like slide was already removed, but let's clean it up just
            # in case

            self.prepare_for_removal()
            self.mc.active_slides.pop(self.name, None)

    def prepare_for_removal(self):
        self.mc.clock.unschedule(self.remove)

        for widget in self.stencil.children:
            if hasattr(widget, 'prepare_for_removal'):  # try swallows too much
                widget.prepare_for_removal()

        self.mc.post_mc_native_event('slide_{}_removed'.format(self.name))

        """event: slide_(name)_removed

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
        for widget in self.stencil.children:
            widget.on_pre_show_slide()

    def on_enter(self, *args):
        del args
        for widget in self.stencil.children:
            widget.on_show_slide()

    def on_pre_leave(self, *args):
        del args
        for widget in self.stencil.children:
            widget.on_pre_slide_leave()

    def on_leave(self, *args):
        del args
        for widget in self.stencil.children:
            widget.on_slide_leave()

    def on_slide_play(self):
        for widget in self.stencil.children:
            widget.on_slide_play()
