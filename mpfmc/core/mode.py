""" Contains the Mode parent class for the Media Controller"""

import logging
from collections import namedtuple

from mpf.core.utility_functions import Util

RemoteMethod = namedtuple('RemoteMethod',
                          'method config_section kwargs priority',
                          verbose=False)
"""RemotedMethod is used by other modules that want to register a method to
be called on mode_start or mode_stop.
"""


class Mode(object):
    """Parent class for in-game mode code."""

    def __init__(self, mc, config, name, path):
        self.mc = mc
        self.config = config
        self.name = name.lower()
        self.path = path

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

        # Call registered remote loader methods
        for item in self.mc.mode_controller.loader_methods:
            if ((item.config_section in self.config and
                    self.config[item.config_section]) or not
                    item.config_section):
                item.method(config=self.config.get(item.config_section),
                            mode=self,
                            mode_path=self.path,
                            root_config_dict=self.config,
                            **item.kwargs)

    def __repr__(self):
        return '<Mode.{}>'.format(self.name)

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, active):
        if self._active != active:
            self._active = active
            self.mc.mode_controller._active_change(self, self._active)

    def configure_mode_settings(self, config):
        """Processes this mode's configuration settings from a config
        dictionary.
        """

        if not ('priority' in config and type(config['priority']) is int):
            config['priority'] = 0

        try:
            self.target = self.mc.targets[config['target']]
        except KeyError:
            self.target = self.mc.targets['default']

        self.config['mode'] = config

    def start(self, priority=None, callback=None, **kwargs):
        """Starts this mode.

        Args:
            priority: Integer value of what you want this mode to run at. If
            you
                don't specify one, it will use the "Mode: priority" setting
                from
                this mode's configuration file.
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

        if type(priority) is int:
            self.priority = priority
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

        for callback in self.mc.mode_controller.stop_methods:
            callback[0](self)

        for item in self.stop_methods:
            item[0](item[1])

        self.stop_methods = list()
