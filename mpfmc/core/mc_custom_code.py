"""Contains the parent class for custom code used in MPF-MC."""
from typing import Callable
from mpf.core.logging import LogMixin

MYPY = False
if MYPY:    # pragma: no cover
    from mpfmc.core.mc import MpfMc     # pylint: disable-msg=cyclic-import,unused-import


class McCustomCode(LogMixin):

    """Custom code in MPF-MC."""

    def __init__(self, mc, name):
        super().__init__()
        self.mc = mc        # type: MpfMc
        self.name = name    # type: str
        self.configure_logging('McCustomCode.' + name, 'basic', 'full')
        self.on_load()
        # wait until MC connected to MPF
        self.mc.events.add_handler("client_connected", self.on_connect)

    def add_mpf_event_handler(self, event: str, handler: Callable):
        """Add an event handler to listen to a MPF event."""
        self.mc.bcp_processor.register_trigger(event)
        return self.mc.events.add_handler(event, handler)

    def post_event_to_mpf_and_mc(self, event, **kwarg):
        """Post an event to MPF and MC."""
        self.mc.post_mc_native_event(event, **kwarg)

    def __repr__(self):  # pragma: no cover
        return '<CustomCode.{}>'.format(self.name)

    def on_connect(self, **kwargs):
        """Called once MC is connected to MPF."""

    def on_load(self):  # pragma: no cover
        """Automatically called when this custom code class loads.

        It's the intention that the custom code writer will overwrite this method.
        """
