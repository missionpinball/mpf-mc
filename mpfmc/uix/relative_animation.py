from kivy.animation import Animation


class RelativeAnimation(Animation):
    """Class that extends the Kivy Animation base class to add relative animation 
    property target values that are calculated when the animation starts."""

    def _initialize(self, widget):
        """Initializes the animation and calculates the property target value
        based on the current value plus the desired delta.
        
        Notes: Do not call the base class _initialize method as this override
        completely replaces the base class method."""
        d = self._widgets[widget.uid] = {
            'widget': widget,
            'properties': {},
            'time': None}

        # get current values and calculate target values
        p = d['properties']
        for key, value in self._animated_properties.items():
            original_value = getattr(widget, key)
            if isinstance(original_value, (tuple, list)):
                original_value = original_value[:]
                target_value = map(lambda x, y: x + y, original_value, value)
            elif isinstance(original_value, dict):
                original_value = original_value.copy()
                target_value = value
            else:
                target_value = original_value + value
            p[key] = (original_value, target_value)

        # install clock
        self._clock_install()
