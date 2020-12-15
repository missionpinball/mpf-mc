""" ModeController for MPF-MC"""

import logging
import os
from collections import namedtuple

from mpf.exceptions.config_file_error import ConfigFileError
from mpfmc.core.mode import Mode


RemoteMethod = namedtuple('RemoteMethod',
                          'method config_section kwargs priority',
                          )
"""RemotedMethod is used by other modules that want to register a method to
be called on mode_start or mode_stop.
"""

# todo create a single ModeController base class for MPF and MPF-MC


class ModeController:
    """Parent class for the Mode Controller. There is one instance of this in
    MPF and it's responsible for loading, unloading, and managing all game
    modes.
    """

    def __init__(self, mc):
        self.mc = mc
        self.log = logging.getLogger('ModeController')

        self.debug = False

        self.active_modes = list()
        self.mode_stop_count = 0

        # The following two lists hold namedtuples of any remote components
        # that need to be notified when a mode object is created and/or
        # started.
        self.loader_methods = list()
        self.start_methods = list()
        self.stop_methods = list()

        self._machine_mode_folders = dict()
        self._mpf_mode_folders = dict()

        if 'modes' in self.mc.machine_config:
            self.mc.events.add_handler('init_phase_2',
                                       self._load_modes)

    def _load_modes(self, **kwargs):
        del kwargs
        # Loads the modes from the modes: section of the machine configuration
        # file.

        self._build_mode_folder_dicts()

        for mode in set(self.mc.machine_config['modes']):
            self.mc.modes[mode] = self._load_mode(mode)

        # initialise modes after loading all of them to prevent races
        for item in self.loader_methods:
            for mode in self.mc.modes.values():
                try:
                    if ((item.config_section in mode.config and
                            mode.config[item.config_section]) or not
                            item.config_section):
                        item.method(config=mode.config.get(item.config_section),
                                    mode=mode,
                                    mode_path=mode.path,
                                    root_config_dict=mode.config,
                                    **item.kwargs)
                except ConfigFileError as e:
                    e.extend("Error while loading mode '{}'".format(mode.name))
                    raise e

    def _load_mode(self, mode_string):
        """Loads a mode, reads in its config, and creates the Mode object.

        Args:
            mode: String name of the mode you're loading. This is the name of
                the mode's folder in your game's machine_files/modes folder.

        """
        if self.debug:
            self.log.debug('Processing mode: %s', mode_string)

        asset_paths = []
        mode_path = None

        if mode_string in self._mpf_mode_folders:
            mode_path = os.path.join(
                self.mc.mpf_path,
                "modes",
                self._mpf_mode_folders[mode_string])
            asset_paths.append(mode_path)

        if mode_string in self._machine_mode_folders:
            mode_path = os.path.join(
                self.mc.machine_path,
                self.mc.machine_config['mpf-mc']['paths']['modes'],
                self._machine_mode_folders[mode_string])
            asset_paths.append(mode_path)

        if not mode_path:
            raise ValueError("No folder found for mode '{}'. Is your mode "
                             "folder in your machine's 'modes' folder?"
                             .format(mode_string))

        config = self.mc.mc_config.get_mode_config(mode_string)

        # validate config
        self.mc.config_validator.validate_config("mode", config['mode'])

        return Mode(self.mc, config, mode_string, mode_path, asset_paths)

    def _build_mode_folder_dicts(self):
        self._mpf_mode_folders = self._get_mode_folder(self.mc.mpf_path)
        self.log.debug("Found MPF Mode folders: %s", self._mpf_mode_folders)

        self._machine_mode_folders = (
            self._get_mode_folder(self.mc.machine_path))
        self.log.debug("Found Machine-specific Mode folders: %s",
                       self._machine_mode_folders)

    def _get_mode_folder(self, base_folder):
        try:
            mode_folders = os.listdir(os.path.join(
                base_folder, self.mc.machine_config['mpf-mc']['paths']['modes']))
        except FileNotFoundError:
            return dict()

        final_mode_folders = dict()

        for folder in mode_folders:

            this_mode_folder = os.path.join(
                base_folder,
                self.mc.machine_config['mpf-mc']['paths']['modes'],
                folder)

            if os.path.isdir(this_mode_folder) and not folder.startswith('_'):
                final_mode_folders[folder] = folder

        return final_mode_folders

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

        if not callable(load_method):
            raise ValueError("Cannot add load method '{}' as it is not"
                             "callable".format(load_method))

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

        if not callable(start_method):
            raise ValueError("Cannot add start method '{}' as it is not"
                             "callable".format(start_method))

        self.start_methods.append(RemoteMethod(method=start_method,
                                               config_section=config_section_name,
                                               priority=priority,
                                               kwargs=kwargs))

        self.start_methods.sort(key=lambda x: x.priority, reverse=True)

    def register_stop_method(self, callback, priority=0):
        # these are universal, in that they're called every time a mode stops
        # priority is the priority they're called. Has nothing to do with mode
        # priority

        if not callable(callback):
            raise ValueError("Cannot add stop method '{}' as it is not"
                             "callable".format(callback))

        self.stop_methods.append((callback, priority))

        self.stop_methods.sort(key=lambda x: x[1], reverse=True)

    def active_change(self, mode, active):
        # called when a mode goes active or inactive

        if active:
            self.active_modes.append(mode)
        else:
            self.active_modes.remove(mode)

        # sort the active mode list by priority
        self.active_modes.sort(key=lambda x: x.priority, reverse=True)
