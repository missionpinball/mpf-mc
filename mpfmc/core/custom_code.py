"""Contains the parent class for custom code used in MPF-MC."""


class CustomCode:

    """Baseclass for custom code in a machine."""

    __slots__ = ["machine", "name", "delay"]

    def __init__(self, mc, name):
        """initialize custom code."""
        self.mc = mc
        self.name = name

        self.on_load()

    def __repr__(self):
        """Return string representation."""
        return '<CustomCode.{}>'.format(self.name)

    def on_load(self):
        """Automatically called when this custom code class loads.

        It's the intention that the programmer will overwrite this method
        in his custom code.
        """
        pass