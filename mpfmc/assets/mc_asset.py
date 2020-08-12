from mpf.core.assets import Asset


# pylint: disable-msg=abstract-method
class McAsset(Asset):

    """Baseclass for all assets in mc."""

    __slots__ = ['__weakref__']

    def __init__(self, machine, name, file, config):
        """Track this asset for potential leaks."""
        super().__init__(machine, name, file, config)
        machine.track_leak_reference(self)
