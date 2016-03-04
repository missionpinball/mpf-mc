from bisect import bisect

from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import Rectangle
from kivy.uix.screenmanager import Screen
from kivy.uix.stencilview import StencilView

from mpfmc.core.mode import Mode
from mpfmc.core.utils import set_position


class Slide(Screen):
    next_id = 0

    @classmethod
    def get_id(cls):
        Slide.next_id += 1
        return Slide.next_id

    def __init__(self, mc, name, config=None, target='default', mode=None,
                 priority=None, **kwargs):
        self.mc = mc
        self.name = name
        self.priority = None
        self.creation_order = Slide.get_id()
        self.pending_widgets = set()

        if not name:
            self.name = 'Anon_{}'.format(self.creation_order)

        if not config:
            config=dict()

        if priority is None:
            try:
                self.priority = mode.priority
            except AttributeError:
                self.priority = 0
        else:
            self.priority = int(priority)

        if mode:
            if isinstance(mode, Mode):
                self.mode = mode
            else:
                self.mode = self.mc.modes[mode]
        else:
            self.mode = None

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

        try:
            self.add_widgets_from_config(config, self.mode, **kwargs)
        except KeyError:
            pass

        self.mc.active_slides[name] = self
        target.add_widget(self)

        # Make the slide not transparent. (Widgets are drawn in reverse order,
        # so the before method draws it on the bottom.)
        with self.canvas.before:
            Color(0, 0, 0, 1)
            Rectangle(size=self.size, pos=(0,0))

    def __repr__(self):
        return '<Slide name={}, priority={}, id={}>'.format(self.name,
            self.priority, self.creation_order)

    def add_widgets_from_library(self, name, mode=None):
        if name not in self.mc.widgets:
            return

        return self.add_widgets_from_config(self.mc.widgets[name], mode)

    def add_widgets_from_config(self, config, mode=None, **kwargs):
        if type(config) is not list:
            config = [config]
        widgets_added = list()

        for widget in config:
            widget_obj = widget['_widget_cls'](mc=self.mc, config=widget,
                                              slide=self, mode=mode,
                                               **kwargs)

            top_widget = widget_obj

            # some widgets like slide frames have parents, so we need to make
            # sure that we add the parent widget to the slide
            while top_widget.parent:
                top_widget = top_widget.parent

            self.add_widget(top_widget)

            widget_obj.pos = set_position(self.width,
                                          self.height,
                                          widget_obj.width,
                                          widget_obj.height,
                                          widget['x'],
                                          widget['y'],
                                          widget['anchor_x'],
                                          widget['anchor_y'])
            widgets_added.append(widget_obj)
        return widgets_added

    def add_widget(self, widget):
        """Adds a widget to this slide.

        Args:
            widget: An MPF-enhanced widget (which will include details like z
                order and what mode created it.

        This method respects the z-order of the widget it's adding and inserts
        it into the proper position in the widget tree. Higher numbered z order
        values will be inserted after (so they draw on top) of existing ones.

        If the new widget has the same priority of existing widgets, the new
        one is inserted after the widgets of that priority, meaning the newest
        widget will be displayed on top of existing ones with the same
        priority.

        """
        z = widget.config['z']

        if z < 0:
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
                                  widget.config['anchor_y'])

    def remove_widgets_by_mode(self, mode):
        for widget in [x for x in self.stencil.children if x.mode == mode]:
            self.stencil.remove_widget(widget)

    def add_widget_to_parent_frame(self, widget):
        """Adds this widget to this slide's parent frame instead of to this
        slide.

        Args:
            widget:
                The widget object.

        Widgets added to the parent slide_frame stay active and visible even
        if the slide in the frame changes.

        Note that negative z-order values tell the widget it should be applied
        to the parent frame instead of the slide, but the absolute value of the
        values is used to control their z-order. e.g. -100 widget shows on top
        of a -50 widget.

        """
        self.parent.parent.parent.add_widget(widget)

    def prepare_for_removal(self, widget=None):
        pass

        # TODO what do we have to do here? I assume something? Remove from
        # active slide list?
