from kivy.uix.screenmanager import Screen

from mc.core.mode import Mode


class Slide(Screen):
    next_id = 0

    @classmethod
    def get_id(cls):
        Slide.next_id += 1
        return Slide.next_id

    def __init__(self, mc, name, config, target='default', mode=None,
                 priority=None, show=True, force=False, **kwargs):
        self.mc = mc
        self.name = name
        self.priority = None
        self.creation_order = Slide.get_id()

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

        if self.mode:
            self.priority += self.mode.priority

        target = mc.targets[target]

        super().__init__(**kwargs)
        self.size = target.size
        self.orig_w, self.orig_h = self.size

        try:
            self.add_widgets_from_config(config)
        except KeyError:
            pass

        self.mc.active_slides[name] = self
        target.add_widget(slide=self, show=show, force=force)

    def __repr__(self):
        return '<Slide name={}, priority={}>'.format(self.name, self.priority)

    def set_position(self, slide, widget, x=None, y=None, h_pos=None,
                     v_pos=None):
        """Calculates the x,y position for the upper-left corner of this
        element
        based on several positioning parameters.

        Args:
            v_pos: String which describes the vertical anchor position this
                calculation should be based on. Options include 'top',
                'bottom',
                and 'center' (or 'middle'). Default is 'center' if no `y`
                parameter is given, and 'top' if there is a `y` parameter.
            h_pos: String which describes the horizontal anchor position this
                calculation should be based on. Options include 'left',
                'right',
                and 'center' (or 'middle'). Default is 'center' if no `x`
                parameter is given, and 'left' if there is an `x` parameter.
            x: The x (horizontal value) you'd like to position this element in.
                If this is an positive integer, it will be the number of pixels
                to the left of the h_pos anchor. If it's negative, it will be
                the number of pixels to the right of the h_pos anchor. If this
                is a float between -1.0 and 1.0, then this will be the percent
                between the left edge and the h_pos anchor for positive values,
                and the right edge and the h_pos anchor
                for negative values.
            y: The y (vertical value) you'd like to position this element in.
                If this is an positive integer, it will be the number of pixels
                below the v_pos anchor. If it's negative, it will be
                the number of pixels above the v_pos anchor. If this
                is a float between -1.0 and 1.0, then this will be the percent
                between the bottom edge and the v_pos anchor for positive
                values, and the top edge and the v_pos anchor for negative
                values.

        """
        try:
            slide_w, slide_h = slide.size
            widget_w, widget_h = widget.size
        except AttributeError:
            return

        # First figure out the anchor:
        if not h_pos:
            if x is not None:  # i.e. `if x:`
                h_pos = 'left'
            else:
                h_pos = 'center'

        if not v_pos:
            if y is not None:  # i.e. `if y:`
                v_pos = 'top'
            else:
                v_pos = 'center'

        # Next get the starting point for x, y based on that anchor
        if v_pos == 'bottom':
            final_y = 0
        elif v_pos == 'top':
            final_y = slide_h - widget_h
        elif v_pos == 'center' or v_pos == 'middle':
            final_y = (slide_h - widget_h) / 2
        else:
            raise ValueError('Received invalid v_pos value:', v_pos)

        if h_pos == 'left':
            final_x = 0
        elif h_pos == 'right':
            final_x = slide_w - widget_w
        elif h_pos == 'center' or h_pos == 'middle':
            final_x = (slide_w - widget_w) / 2
        else:
            raise ValueError("Received invalid 'h_pos' value:", h_pos)

        # Finally shift x, y based on values passed.
        if x is not None:
            if -1.0 < x < 1.0:
                final_x += x * slide_w
            else:
                final_x += x

        if y is not None:
            if -1.0 < y < 1.0:
                final_y += y * slide_h
            else:
                final_y += y

        return final_x, final_y

    def add_widgets_from_library(self, name, mode=None):
        if name not in self.mc.widget_configs:
            return

        return self.add_widgets_from_config(self.mc.widget_configs[name], mode)

    def add_widgets_from_config(self, config, mode=None):
        if type(config) is not list:
            config = [config]
        widgets_added = list()

        for widget in config:
            widget_obj = widget['widget_cls'](mc=self, config=widget,
                                              slide=self, mode=mode)
            self.add_widget(widget_obj)
            widget_obj.texture_update()
            widget_obj.size = widget_obj.texture_size
            widget_obj.pos = self.set_position(self, widget_obj, widget['x'],
                                               widget['y'], widget['h_pos'],
                                               widget['v_pos'])
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
        my_priority = widget.config['z']

        if my_priority < 0:
            self.add_widget_to_parent_frame(widget)
            return

        index = 0

        # this might be able to be a count of a list comprehension or something

        for i, w in enumerate(self.children):
            if w.config['z'] <= my_priority:
                index = i + 1
                # need to increment index until we hit the next priority
                if my_priority < w.config['z']:
                    break

        # BTW I have no idea why this simpler code doesn't work:
        # for i, w in enumerate(self.children):
        #     if w.config['z'] > my_priority:
        #         index = i
        #         break

        super().add_widget(widget, index)

    def remove_widgets_by_mode(self, mode):
        for widget in [x for x in self.children if x.mode == mode]:
            self.remove_widget(widget)

    def add_widget_to_parent_frame(self, widget):
        """Adds this widget to this slide's parent frame instead of to this
        slide.

        Args:
            widget:
                The widget object.

        Widgets added to the parent slide_frame stay active and visible even
        if the slide in the frame changes.

        Note that slide_frame z-order is negative, with more negative values
        showing on top of less negative values. (Think of it like they're
        moving farther away from the slide.) e.g. -100 widget shows on top of
        -50 widget.

        """
        self.parent.add_widget(widget)
