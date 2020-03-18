""" Contains the Mode parent class for the Media Controller"""

import logging
from collections import namedtuple

RemoteMethod = namedtuple('RemoteMethod',
                          'method config_section kwargs priority',
                          )
"""RemotedMethod is used by other modules that want to register a method to
be called on mode_start or mode_stop.
"""


# pylint: disable-msg=too-many-instance-attributes
class Mode:
    """Parent class for in-game mode code."""

    __slots__ = ["mc", "config", "name", "path", "asset_paths", "log", "priority", "_active", "stop_methods",
                 "start_callback", "stop_callback", "event_handlers", "target"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, mc, config, name, path, asset_paths):
        self.mc = mc
        self.config = config
        self.name = name.lower()
        self.path = path
        self.asset_paths = asset_paths

        self.log = logging.getLogger('Mode.' + name)

        self.priority = 0
        self._active = False
        self.stop_methods = list()
        self.start_callback = None
        self.stop_callback = None
        self.event_handlers = set()
        self.target = None

        if 'mode' in self.config:
            self.configure_mode_settings(config['mode'])

    def __repr__(self):
        return '<Mode.{}>'.format(self.name)

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, active):
        if self._active != active:
            self._active = active
            self.mc.mode_controller.active_change(self, self._active)

    def configure_mode_settings(self, config):
        """Processes this mode's configuration settings from a config
        dictionary.
        """

        if not ('priority' in config and isinstance(config['priority'], int)):
            config['priority'] = 0

        try:
            self.target = self.mc.targets[config['target']]
        except KeyError:
            self.target = self.mc.targets['default']

        self.config['mode'] = config

    def start(self, mode_priority=None, callback=None, **kwargs):
        """Starts this mode.

        Args:
            mode_ priority: Integer value of what you want this mode to run at.
                If you don't specify one, it will use the "Mode: priority"
                setting from this mode's configuration file.
            **kwargs: Catch-all since this mode might start from events with
                who-knows-what keyword arguments.

        Warning: You can safely call this method, but do not override it in
        your
        mode code. If you want to write your own mode code by subclassing Mode,
        put whatever code you want to run when this mode starts in the
        mode_start method which will be called automatically.

        """

        # todo might want to use this
        del callback
        del kwargs

        if isinstance(mode_priority, int):
            self.priority = mode_priority
        else:
            self.priority = self.config['mode']['priority']

        self.log.debug('Mode Start. Priority: %s', self.priority)

        self.active = True

        for item in self.mc.mode_controller.start_methods:
            if item.config_section in self.config or not item.config_section:
                self.stop_methods.append(item.method(
                    config=self.config.get(item.config_section),
                    priority=self.priority,
                    mode=self,
                    **item.kwargs))

    @staticmethod
    def is_game_mode() -> bool:
        """Return false since mc does not have game modes."""
        return False

    def stop(self, callback=None, **kwargs):
        """Stops this mode.

        Args:
            **kwargs: Catch-all since this mode might start from events with
                who-knows-what keyword arguments.

        Warning: You can safely call this method, but do not override it in
        your
        mode code. If you want to write your own mode code by subclassing Mode,
        put whatever code you want to run when this mode stops in the
        mode_stop method which will be called automatically.

        """

        # todo might want to use this?
        del callback

        del kwargs

        self.log.debug('Mode Stop.')

        self.priority = 0
        self.active = False

        for callback_func in self.mc.mode_controller.stop_methods:
            callback_func[0](self)

        for item in self.stop_methods:
            item[0](item[1])

        self.stop_methods = list()
