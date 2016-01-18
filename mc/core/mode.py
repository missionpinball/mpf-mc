""" Contains the Mode parent class for the Media Controller"""

import logging
from collections import namedtuple

from mpf.system.utility_functions import Util

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

        # todo

        # for asset_manager in self.mc.asset_managers.values():
        #
        #     config_data = self.config.get(asset_manager.config_section,
        # dict())
        #
        #     self.config[asset_manager.config_section] = (
        #         asset_manager.register_assets(config=config_data,
        #                                       mode_path=self.path))

        # Call registered remote loader methods
        for item in self.mc.mode_controller.loader_methods:
            if (item.config_section in self.config and
                    self.config[item.config_section]):
                item.method(config=self.config[item.config_section],
                            mode_path=self.path,
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

        if 'start_events' in config:
            config['start_events'] = Util.string_to_list(
                    config['start_events'])
        else:
            config['start_events'] = list()

        if 'stop_events' in config:
            config['stop_events'] = Util.string_to_list(
                    config['stop_events'])
        else:
            config['stop_events'] = list()

        # register mode start events
        if 'start_events' in config:
            for event in config['start_events']:
                self.mc.events.add_handler(event, self.start)

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
        if type(priority) is int:
            self.priority = priority
        else:
            self.priority = self.config['mode']['priority']

        self.log.info('Mode Start. Priority: %s', self.priority)

        self.active = True

        for item in self.mc.mode_controller.start_methods:
            if item.config_section in self.config:
                self.stop_methods.append(
                        item.method(config=self.config[item.config_section],
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
        self.log.debug('Mode Stop.')

        self.priority = 0
        self.active = False

        for item in self.stop_methods:
            try:
                item[0](item[1])
            except TypeError:
                pass

        self.stop_methods = list()

        self.remove_slides()
        self.remove_widgets()

    def remove_slides(self):
        """Removes all the slides from this mode from the active targets."""

        target_list = set(self.mc.targets.values())
        for target in target_list:
            for screen in [x for x in target.screens if x.mode == self]:
                target.remove_slide(screen)

    def remove_widgets(self):
        # remove widgets from slides
        for slide in self.mc.active_slides.values():
            slide.remove_widgets_by_mode(self)

        # remove widgets from slide frame parents
        target_list = set(self.mc.targets.values())
        for target in target_list:
            for widget in [x for x in target.parent.children if x.mode ==
                    self]:

                target.parent.remove_widget(widget)
