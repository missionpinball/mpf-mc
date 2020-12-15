"""Contains the parent class for Scriptlets used in MPF-MC."""


class Scriptlet:

    """DEPRECATED scriptlet in MPF-MC."""

    def __init__(self, mc, name):
        self.mc = mc
        self.name = name
        self.on_load()

    def __repr__(self):  # pragma: no cover
        return '<Scriptlet.{}>'.format(self.name)

    def on_load(self):  # pragma: no cover
        """Automatically called when this Scriptlet loads. It's the intention
        that the Scriptlet writer will overwrite this method in the Scriptlet.
        """
