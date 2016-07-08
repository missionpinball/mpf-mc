"""Contains the MpfMc base class, which is the main App instance for the
mpf-mc.

"""
import importlib
import os
import queue
import threading
import time
import logging

from kivy.app import App
from kivy.clock import Clock
from kivy.resources import resource_add_path
from kivy.logger import Logger

# The following line is needed to allow mpfmc modules to use the getLogger(name) method
logging.Logger.manager.root = Logger

from mpfmc.assets.video import VideoAsset
from mpfmc.core.bcp_processor import BcpProcessor
from mpfmc.core.config_processor import ConfigProcessor
from mpfmc.core.mode_controller import ModeController
from mpfmc.uix.transitions import TransitionManager
from mpfmc.core.config_collection import create_config_collections

import mpf
import mpfmc
from mpfmc._version import __version__
from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.config_validator import ConfigValidator
from mpf.core.events import EventManager
from mpf.core.player import Player
from mpf.core.assets import AssetManager
from mpfmc.assets.image import ImageAsset

try:
    from mpfmc.core.audio import SoundSystem
    from mpfmc.assets.sound import SoundAsset
except ImportError:
    SoundSystem = None
    SoundAsset = None
    logging.warning("mpfmc.core.audio library could not be loaded. Audio "
                    "features will not be available")


class MpfMc(App):
    def __init__(self, options, config, machine_path,
                 thread_stopper=None, **kwargs):

        self.log = logging.getLogger('mpfmc')
        self.log.info("Mission Pinball Framework Media Controller v%s", __version__)
        super().__init__(**kwargs)

        self.options = options
        self.machine_config = config
        self.log.info("Machine path: %s", machine_path)
        self.machine_path = machine_path
        self.clock = Clock
        self.log.info("Starting clock at %sHz", Clock._max_fps)
        self._boot_holds = set()
        self.mpf_path = os.path.dirname(mpf.__file__)
        self.modes = CaseInsensitiveDict()
        self.player_list = list()
        self.player = None
        self.num_players = 0
        self.bcp_client_connected = False

        self.animation_configs = dict()
        self.active_slides = dict()
        self.scriptlets = list()

        self.register_boot_hold('init')
        self.displays = CaseInsensitiveDict()
        self.machine_vars = CaseInsensitiveDict()
        self.machine_var_monitor = False
        self.monitors = dict()
        self.targets = dict()
        """Dict which contains all the active slide frames in the machine that
        a slide can target. Will always contain an entry called 'default'
        which will be used if a slide doesn't specify targeting.
        """

        self.keyboard = None
        self.physical_dmd = None
        self.physical_rgb_dmd = None
        self.crash_queue = queue.Queue()
        self.ticks = 0
        self.start_time = 0
        self.is_init_done = False

        if thread_stopper:
            self.thread_stopper = thread_stopper
        else:
            self.thread_stopper = threading.Event()

        # Core components
        self.config_validator = ConfigValidator(self)
        self.events = EventManager(self)
        self.mode_controller = ModeController(self)
        create_config_collections(self, self.machine_config['mpf-mc'][
            'config_collections'])
        ConfigValidator.load_config_spec()

        self.config_processor = ConfigProcessor(self)
        self.transition_manager = TransitionManager(self)

        # Add local machine fonts path
        if os.path.isdir(os.path.join(self.machine_path,
                self.machine_config['mpf-mc']['paths']['fonts'])):

            resource_add_path(os.path.join(self.machine_path,
                self.machine_config['mpf-mc']['paths']['fonts']))

        # Add mpfmc fonts path
        resource_add_path(os.path.join(os.path.dirname(mpfmc.__file__),
                                       'fonts'))

        # Initialize the sound system (must be done prior to creating the AssetManager).
        # If the sound system is not available, do not load any other sound-related modules.
        if SoundSystem is None:
            self.sound_system = None
        else:
            self.sound_system = SoundSystem(self)

        self.asset_manager = AssetManager(self)
        self.bcp_processor = BcpProcessor(self)

        # Asset classes
        ImageAsset.initialize(self)
        VideoAsset.initialize(self)

        # Only initialize sound assets if sound system is loaded and enabled
        if self.sound_system is not None and self.sound_system.enabled:
            SoundAsset.extensions = tuple(
                self.sound_system.audio_interface.supported_extensions())
            SoundAsset.initialize(self)
        else:
            # If the sound system is not loaded or enabled, remove the
            # sound_player from the list of config_player modules to setup
            del self.machine_config['mpf-mc']['config_players']['sound']

        self.clock.schedule_interval(self._check_crash_queue, 1)

    def get_system_config(self):
        return self.machine_config['mpf-mc']

    def validate_machine_config_section(self, section):
        if section not in ConfigValidator.config_spec:
            return

        if section not in self.machine_config:
            self.config[section] = dict()

        self.machine_config[section] = self.config_validator.validate_config(
            section, self.machine_config[section], section)

    def get_config(self):
        return self.machine_config

    def register_boot_hold(self, hold):
        # print('registering boot hold', hold)
        self._boot_holds.add(hold)

    def clear_boot_hold(self, hold):
        # print('clearing boot hold', hold)
        self._boot_holds.remove(hold)
        if not self._boot_holds:
            self.init_done()

    def _register_config_players(self):
        # todo move this to config_player module

        for name, module in self.machine_config['mpf-mc'][
                'config_players'].items():
            imported_module = importlib.import_module(module)
            setattr(self, '{}_player'.format(name),
                    imported_module.mc_player_cls(self))

    def displays_initialized(self, *args):
        del args
        from mpfmc.uix.window import Window
        Window.initialize(self)
        self.events.post('displays_initialized')
        '''event: displays_initialized
        desc: Posted as soon as MPF MC displays have been initialized.

        Note that this event is used as part of the internal MPF-MC startup
        process. In some cases it will be posted *before* the slide_player is
        ready, meaning that you *CANNOT* use this event to post slides or play
        sounds.

        Instead, use the *mc_ready* event, which is posted as early as possible
        once the slide player and sound players are setup.

        Note that this event is generated by the media controller and does not
        exist on the MPF side of things.

        Also note that if you're using a media controller other than the MPF-MC
        (such as the Unity 3D backbox controller), then this event won't exist.

        '''
        self.events.process_event_queue()
        self._init()

    def create_physical_dmd(self, fps):
        if 'physical_dmd' in self.machine_config and not self.physical_dmd:
            from mpfmc.core.physical_dmd import PhysicalDmd
            self.physical_dmd = PhysicalDmd(
                self, self.machine_config['physical_dmd'], fps)

    def create_physical_rgb_dmd(self, fps):
        if ('physical_rgb_dmd' in self.machine_config and
                not self.physical_rgb_dmd):
            from mpfmc.core.physical_dmd import PhysicalRgbDmd
            self.physical_rgb_dmd = PhysicalRgbDmd(
                self, self.machine_config['physical_rgb_dmd'], fps)

    def _init(self):
        # Since the window is so critical in Kivy, we can't continue the
        # boot process until the window is setup, and we can't set the
        # window up until the displays are initialized.

        self._register_config_players()
        self.events.post("init_phase_1")
        # no events docstring as this event is also in mpf
        self.events.process_event_queue()
        self.events.post("mc_ready")
        '''event: mc_ready
        desc: Posted when the MPF-MC is available to start showing slides and
        playing sounds.

        Note that this event does not mean the MC is done loading. Instead it's
        posted at the earliest possible moment that the core MC components are
        available, meaning you can trigger "boot" slides from this event (which
        could in turn be used to show asset loading status, boot progress,
        etc.)
        '''

        self.events.process_event_queue()
        self.events.post("init_phase_2")
        # no events docstring as this event is also in mpf
        self.events.process_event_queue()
        self.events.post("init_phase_3")
        # no events docstring as this event is also in mpf
        self.events.process_event_queue()
        self._load_scriptlets()
        self.events.post("init_phase_4")
        # no events docstring as this event is also in mpf
        self.events.process_event_queue()
        self.events.post("init_phase_5")
        # no events docstring as this event is also in mpf
        self.events.process_event_queue()
        self.clear_boot_hold('init')

    def init_done(self):
        self.is_init_done = True
        ConfigValidator.unload_config_spec()
        self.events.post("init_done")
        # no events docstring as this event is also in mpf
        self.events.process_event_queue()

        self.reset()

    def build(self):
        self.start_time = time.time()
        self.ticks = 0
        self.clock.schedule_interval(self.tick, 0)

    def on_stop(self):
        self.log.info("Stopping...")
        self.thread_stopper.set()

        try:
            self.log.info("Loop rate {}Hz".format(round(
                          self.ticks / (time.time() - self.start_time), 2)))
        except ZeroDivisionError:
            pass

    def reset(self, **kwargs):
        del kwargs
        self.player = None
        self.player_list = list()

        self.events.post('mc_reset_phase_1')
        '''event: mc_reset_phase_1
        desc: Posted on the MPF-MC only (e.g. not in MPF). This event is used
        internally as part of the MPF-MC reset process.
        '''
        self.events.process_event_queue()
        self.events.post('mc_reset_phase_2')
        '''event: mc_reset_phase_2
        desc: Posted on the MPF-MC only (e.g. not in MPF). This event is used
        internally as part of the MPF-MC reset process.
        '''
        self.events.process_event_queue()
        self.events.post('mc_reset_phase_3')
        '''event: mc_reset_phase_3
        desc: Posted on the MPF-MC only (e.g. not in MPF). This event is used
        internally as part of the MPF-MC reset process.
        '''
        self.events.process_event_queue()

    def game_start(self, **kargs):
        self.player = None
        self.player_list = list()
        self.num_players = 0
        self.events.post('game_started', **kargs)
        # no events docstring as this event is also in mpf

    def game_end(self, **kwargs):
        self.player = None
        self.events.post('game_ended', **kwargs)
        # no events docstring as this event is also in mpf

    def add_player(self, player_num):
        if player_num > len(self.player_list):
            player = Player(self, self.player_list)

            self.events.post('player_add_success', player=player,
                             num=player_num)
            # no events docstring as this event is also in mpf

    def update_player_var(self, name, value, player_num):
        try:
            self.player_list[int(player_num) - 1][name] = value
        except (IndexError, KeyError):
            pass

    def player_start_turn(self, player_num):
        if ((self.player and self.player.number != player_num) or
                not self.player):

            try:
                self.player = self.player_list[int(player_num) - 1]
                self.events.post('player_turn_start', number=player_num,
                                 player=self.player)
            except IndexError:
                self.log.error('Received player turn start for player %s, but '
                               'only %s player(s) exist',
                               player_num, len(self.player_list))

    def set_machine_var(self, name, value, change, prev_value):
        self.machine_vars[name] = value

        if change:
            self.log.debug("Setting machine_var '%s' to: %s, (prior: %s, "
                           "change: %s)", name, value, prev_value,
                           change)
            self.events.post('machine_var_' + name,
                             value=value,
                             prev_value=prev_value,
                             change=change)
            # no events docstring as this event is also in mpf

        if self.machine_var_monitor:
            for callback in self.monitors['machine_var']:
                callback(name=name, value=self.vars[name],
                         prev_value=prev_value, change=change)

    def tick(self, time):
        del time
        self.ticks += 1
        self.events.process_event_queue()

    def _load_scriptlets(self):
        if 'mc_scriptlets' in self.machine_config:
            self.machine_config['mc_scriptlets'] = self.machine_config[
                'mc_scriptlets'].split(' ')

            for scriptlet in self.machine_config['mc_scriptlets']:
                i = __import__(
                    self.machine_config['mpf-mc']['paths']['scriptlets'] +
                    '.' + scriptlet.split('.')[0], fromlist=[''])

                self.scriptlets.append(getattr(i, scriptlet.split('.')[1])
                                       (mc=self,
                                        name=scriptlet.split('.')[1]))

    def _check_crash_queue(self, time):
        del time
        try:
            crash = self.crash_queue.get(block=False)
        except queue.Empty:
            pass
        else:
            self.log.info("Shutting down due to child thread crash")
            self.log.info("Crash details: %s", crash)
            self.stop()


    def register_monitor(self, monitor_class, monitor):
        """Registers a monitor.

        Args:
            monitor_class: String name of the monitor class for this monitor
                that's being registered.
            monitor: String name of the monitor.

        MPF uses monitors to allow components to monitor certain internal
        elements of MPF.

        For example, a player variable monitor could be setup to be notified of
        any changes to a player variable, or a switch monitor could be used to
        allow a plugin to be notified of any changes to any switches.

        The MachineController's list of registered monitors doesn't actually
        do anything. Rather it's a dictionary of sets which the monitors
        themselves can reference when they need to do something. We just needed
        a central registry of monitors.

        """
        if monitor_class not in self.monitors:
            self.monitors[monitor_class] = set()

        self.monitors[monitor_class].add(monitor)
