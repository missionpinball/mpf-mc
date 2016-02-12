""" """

import logging
import os
from collections import namedtuple

from mpf.mc.core.mode import Mode
from mpf.core.config_processor import ConfigProcessor
from mpf.core.utility_functions import Util

RemoteMethod = namedtuple('RemoteMethod',
                          'method config_section kwargs priority',
                          verbose=False)
"""RemotedMethod is used by other modules that want to register a method to
be called on mode_start or mode_stop.
"""


class ModeController(object):
    """Parent class for the Mode Controller. There is one instance of this in
    MPF and it's responsible for loading, unloading, and managing all game
    modes.
    """

    def __init__(self, mc):
        self.mc = mc
        self.log = logging.getLogger('ModeController')

        self.active_modes = list()
        self.mode_stop_count = 0

        # The following two lists hold namedtuples of any remote components
        # thatneed to be notified when a mode object is created and/or started.
        self.loader_methods = list()
        self.start_methods = list()

        if 'modes' in self.mc.machine_config:
            self.mc.events.add_handler('init_phase_2',
                                       self._load_modes)

    def _load_modes(self):
        # Loads the modes from the Modes: section of the machine configuration
        # file.

        for mode in set(self.mc.machine_config['modes']):
            self.mc.modes[mode] = self._load_mode(mode)

    def _load_mode(self, mode_string):
        """Loads a mode, reads in its config, and creates the Mode object.

        Args:
            mode: String name of the mode you're loading. This is the name of
                the mode's folder in your game's machine_files/modes folder.

        """
        self.log.debug('Processing mode: %s', mode_string)

        config = dict()

        # find the folder for this mode:
        mode_path = os.path.join(self.mc.machine_path,
                                 self.mc.machine_config['mpf_mc']['paths'][
                                     'modes'], mode_string)

        if not os.path.exists(mode_path):
            mode_path = os.path.abspath(os.path.join('mpf',
                                                     self.mc.machine_config[
                                                         'mpf_mc']['paths'][
                                                         'modes'],
                                                     mode_string))

        # Is there an MPF default config for this mode? If so, load it first
        mpf_mode_config = os.path.join(
                'mpf',
                self.mc.machine_config['mpf_mc']['paths']['modes'],
                mode_string,
                'config',
                mode_string + '.yaml')

        if os.path.isfile(mpf_mode_config):
            config = ConfigProcessor.load_config_file(mpf_mode_config)

        # Now figure out if there's a machine-specific config for this mode,
        #  and
        # if so, merge it into the config

        mode_config_folder = os.path.join(self.mc.machine_path,
                                          self.mc.machine_config['mpf_mc'][
                                              'paths']['modes'], mode_string,
                                          'config')

        found_file = False
        for path, _, files in os.walk(mode_config_folder):
            for file in files:
                file_root, file_ext = os.path.splitext(file)

                if file_root == mode_string:
                    config = Util.dict_merge(config,
                                             ConfigProcessor.load_config_file(
                                                     os.path.join(path, file)))
                    found_file = True
                    break

            if found_file:
                break

        return Mode(self.mc, config, mode_string, mode_path)

    def register_load_method(self, load_method, config_section_name=None,
                             priority=0, **kwargs):
        """Used by system components, plugins, etc. to register themselves with
        the Mode Controller for anything they need a mode to do when it's
        registered.

        Args:
            load_method: The method that will be called when this mode code
                loads.
            config_section_name: An optional string for the section of the
                configuration file that will be passed to the load_method when
                it's called.
            priority: Int of the relative priority which allows remote methods
                to be called in a specific order. Default is 0. Higher values
                will be called first.
            **kwargs: Any additional keyword arguments specified will be passed
                to the load_method.

        Note that these methods will be called once, when the mode code is
        first
        initialized during the MPF boot process.

        """
        self.loader_methods.append(RemoteMethod(method=load_method,
                                                config_section=config_section_name,
                                                kwargs=kwargs,
                                                priority=priority))

        self.loader_methods.sort(key=lambda x: x.priority, reverse=True)

    def register_start_method(self, start_method, config_section_name=None,
                              priority=0, **kwargs):
        """Used by system components, plugins, etc. to register themselves with
        the Mode Controller for anything that they a mode to do when it starts.

        Args:
            start_method: The method that will be called when this mode code
                loads.
            config_section_name: An optional string for the section of the
                configuration file that will be passed to the start_method when
                it's called.
            priority: Int of the relative priority which allows remote methods
                to be called in a specific order. Default is 0. Higher values
                will be called first.
            **kwargs: Any additional keyword arguments specified will be passed
                to the start_method.

        Note that these methods will be called every single time this mode is
        started.

        """
        self.start_methods.append(RemoteMethod(method=start_method,
                                               config_section=config_section_name,
                                               priority=priority,
                                               kwargs=kwargs))

        self.start_methods.sort(key=lambda x: x.priority, reverse=True)

    def _active_change(self, mode, active):
        # called when a mode goes active or inactive

        if active:
            self.active_modes.append(mode)
        else:
            self.active_modes.remove(mode)

        # sort the active mode list by priority
        self.active_modes.sort(key=lambda x: x.priority, reverse=True)

        self.dump()

    def dump(self):
        """Dumps the current status of the running modes to the log file."""

        self.log.info('================== ACTIVE MODES ======================')

        for mode in self.active_modes:
            if mode.active:
                self.log.info('%s : %s', mode.name, mode.priority)

        self.log.info('======================================================')
