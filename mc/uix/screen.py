from kivy.uix.screenmanager import Screen as KivyScreen

from mc.core.mode import Mode


class Screen(KivyScreen):
    def __init__(self, mc, name, config, screen_manager, mode=None,
                 priority=None, **kwargs):
        super().__init__(**kwargs)

        self.mc = mc

        self.size = screen_manager.size
        self.orig_w, self.orig_h = self.size

        self.name = name

        if mode:
            if isinstance(mode, Mode):
                self.mode = mode
            else:
                self.mode = self.mc.modes[mode]
        else:
            self.mode = None

        if priority is None:
            try:
                self.priority = mode.priority
            except AttributeError:
                self.priority = 0
        else:
            self.priority = int(priority)

        self._create_widgets_from_config(config)

        screen_manager.add_widget(self)

    def _create_widgets_from_config(self, config):
        for widget in config:
            widget_obj = widget['widget_cls'](mc=self, config=widget,
                                              screen=self)

            self.add_widget(widget_obj)
            widget_obj.texture_update()
            widget_obj.size = widget_obj.texture_size
            widget_obj.pos = self.set_position(self, widget_obj, widget['x'],
                                               widget['y'], widget['h_pos'],
                                               widget['v_pos'])

    def set_position(self, screen, widget, x=None, y=None, h_pos=None,
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
            screen_w, screen_h = screen.size
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
            final_y = screen_h - widget_h
        elif v_pos == 'center' or v_pos == 'middle':
            final_y = (screen_h - widget_h) / 2
        else:
            raise ValueError('Received invalid v_pos value:', v_pos)

        if h_pos == 'left':
            final_x = 0
        elif h_pos == 'right':
            final_x = screen_w - widget_w
        elif h_pos == 'center' or h_pos == 'middle':
            final_x = (screen_w - widget_w) / 2
        else:
            raise ValueError("Received invalid 'h_pos' value:", h_pos)

        # Finally shift x, y based on values passed.
        if x is not None:
            if -1.0 < x < 1.0:
                final_x += x * screen_w
            else:
                final_x += x

        if y is not None:
            if -1.0 < y < 1.0:
                final_y += y * screen_h
            else:
                final_y += y

        return final_x, final_y

    def add_widget(self, widget, index=0):
        super().add_widget(widget, index)

        # sort widgets

    def _sort_widgets(self):
        pass
