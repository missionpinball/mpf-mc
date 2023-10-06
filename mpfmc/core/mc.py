"""Contains the MpfMc base class, which is the main App instance for the
mpf-mc."""
import gc
import importlib
import logging
import os
import queue
import sys
import threading
import time
import weakref
from packaging import version
from pathlib import Path
from typing import Dict

import mpf
from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.logger import Logger
from kivy.resources import resource_add_path
from mpf._version import __version__ as __mpfversion__
from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.config_loader import MpfMcConfig
from mpf.core.config_validator import ConfigValidator
from mpf.core.device_manager import DeviceCollection
from mpf.core.events import EventManager
from mpf.core.player import Player
from mpf.core.rgb_color import RGBColor
from mpf.core.utility_functions import Util

import mpfmc
from mpfmc._version import __version__, __mpf_version_required__
from mpfmc.assets.bitmap_font import BitmapFontAsset
from mpfmc.assets.image import ImageAsset
from mpfmc.assets.video import VideoAsset
from mpfmc.core.assets import ThreadedAssetManager
from mpfmc.core.bcp_processor import BcpProcessor
from mpfmc.core.config_collection import create_config_collections
from mpfmc.core.config_processor import ConfigProcessor
from mpfmc.core.dmd import Dmd, RgbDmd
from mpfmc.core.mc_placeholder_manager import McPlaceholderManager
from mpfmc.core.mc_settings_controller import McSettingsController
from mpfmc.core.mode_controller import ModeController
from mpfmc.uix.effects import EffectsManager
from mpfmc.uix.transitions import TransitionManager

try:
    # The following two lines are needed because of circular dependencies.
    # These Cython based imports also import assets.sound which then import these (causing a loop/circle).
    # Loading these first resolves an issue on Windows that otherwise causes audio to not load.
    from mpfmc.core.audio.audio_interface import AudioInterface
    from mpfmc.core.audio.audio_exception import AudioException

    from mpfmc.assets.sound import SoundAsset
    from mpfmc.core.audio import SoundSystem
except ImportError as e:
    SoundSystem = None
    SoundAsset = None
    logging.warning("Error importing MPF-MC audio library. Audio will be disabled.")
    logging.warning("*** [[[[[[[[[[[[[[[[[[[ NO AUDIO ]]]]]]]]]]]]]]]]] ***")
    logging.exception(str(e))

# The following line is needed to allow mpfmc modules to use the
# getLogger(name) method
logging.Logger.manager.root = Logger


# pylint: disable-msg=too-many-instance-attributes
class MpfMc(App):

    """Kivy app for the mpf media controller."""

    # pylint: disable-msg=too-many-statements
    def __init__(self, options, config: MpfMcConfig,
                 thread_stopper=None):

        self.log = logging.getLogger('mpfmc')
        self.log.info(f"Mission Pinball Framework Media Controller (MPF-MC) v{__version__}. Requires MPF v{__mpf_version_required__} or newer.")
        self.log.info(f"Found MPF v{__mpfversion__}")

        if version.parse(__mpfversion__) < version.parse(__mpf_version_required__):
            raise ValueError(f"MPF MC requires at least MPF v{__mpf_version_required__}. You have MPF v{__mpfversion__}")

        super().__init__()

        self.options = options
        self.machine_path = config.get_machine_path()
        self.log.info("Machine path: %s", self.machine_path)

        # load machine into path to load modules
        if self.machine_path not in sys.path:
            sys.path.append(self.machine_path)
        self.mc_config = config
        self.config_validator = ConfigValidator(self, config.get_config_spec())
        self.machine_config = self.mc_config.get_machine_config()
        self.config = self.machine_config

        self.clock = Clock
        # pylint: disable-msg=protected-access
        self.log.info("Starting clock at %sHz", Clock._max_fps)
        self._boot_holds = set()
        self.is_init_done = threading.Event()
        self.mpf_path = os.path.dirname(mpf.__file__)
        self.modes = CaseInsensitiveDict()
        self.player_list = list()
        self.player = None
        self.num_players = 0
        self.bcp_client_connected = False
        self.placeholder_manager = McPlaceholderManager(self)
        self.settings = McSettingsController(self)

        self.animation_configs = dict()
        self.active_slides = dict()
        self.custom_code = list()

        self.register_boot_hold('init')
        self.displays = DeviceCollection(self, "displays", "displays")
        self.machine_vars = CaseInsensitiveDict()
        self.machine_var_monitor = False
        self.monitors = dict()
        self.targets = dict()
        """Dict which contains all the active slide frames in the machine that
        a slide can target. Will always contain an entry called 'default'
        which will be used if a slide doesn't specify targeting.
        """

        self.keyboard = None
        self.dmds = []
        self.rgb_dmds = []
        self.crash_queue = queue.Queue()
        self.ticks = 0
        self.start_time = 0
        self.debug_refs = []

        MYPY = False    # NOQA
        if MYPY:  # pragma: no cover
            self.videos = None               # type: Dict[str, VideoAsset]

        if thread_stopper:
            self.thread_stopper = thread_stopper
        else:
            self.thread_stopper = threading.Event()

        # Core components
        self.events = EventManager(self)
        self.mode_controller = ModeController(self)
        create_config_collections(self, self.machine_config['mpf-mc']['config_collections'])
        self._preprocess_config(self.config)

        self.config_processor = ConfigProcessor(self)
        self.transition_manager = TransitionManager(self)
        self.effects_manager = EffectsManager(self)

        self._set_machine_path()

        self._load_font_paths()

        # Initialize the sound system (must be done prior to creating the AssetManager).
        # If the sound system is not available, do not load any other sound-related modules.
        if SoundSystem is None or self.options.get("no_sound"):
            self.sound_system = None
        else:
            self.sound_system = SoundSystem(self)
            if self.sound_system.audio_interface is None:
                self.sound_system = None



        self.asset_manager = ThreadedAssetManager(self)
        self.bcp_processor = BcpProcessor(self)

        # Asset classes
        ImageAsset.initialize(self)
        VideoAsset.initialize(self)
        BitmapFontAsset.initialize(self)

        self._initialize_sound_system()

        self.clock.schedule_interval(self._check_crash_queue, 1)

        self.events.add_handler("client_connected", self._create_dmds)
        self.events.add_handler("player_turn_start", self.player_start_turn)

        self.create_machine_var('mpfmc_ver', __version__)
        # force setting it here so we have it before MPF connects
        self.receive_machine_var_update('mpfmc_ver', __version__, 0, True)

    def _load_named_colors(self):
        for name, color in self.machine_config.get('named_colors', {}).items():
            RGBColor.add_color(name, color)

    def track_leak_reference(self, element):
        """Track elements to find leaks."""
        if not self.options["production"]:
            self.debug_refs.append(weakref.ref(element))
            # cleanup all dead references
            self.debug_refs = [element for element in self.debug_refs if element()]

    @staticmethod
    def _preprocess_config(config):
        kivy_config = config['kivy_config']

        try:
            kivy_config['graphics'].update(config['window'])
        except KeyError:
            pass

        if ('top' in kivy_config['graphics'] and
                'left' in kivy_config['graphics']):
            kivy_config['graphics']['position'] = 'custom'

        for section, settings in kivy_config.items():
            for k, v in settings.items():
                try:
                    if k in Config[section]:
                        Config.set(section, k, v)
                except KeyError:
                    continue

        try:  # config not validated yet, so we use try
            if config['window']['exit_on_escape']:
                Config.set('kivy', 'exit_on_escape', '1')
        except KeyError:
            pass

        Config.set('graphics', 'maxfps', int(config['mpf-mc']['fps']))

    def _load_config(self):
        files = [os.path.join(
            mpfmc.__path__[0], self.options["mcconfigfile"])]
        for config_file in self.options["configfile"]:
            files.append(os.path.join(self.machine_path, "config", config_file))
        mpf_config = self.mpf_config_processor.load_config_files_with_cache(files, "machine", True)

        self._preprocess_config(mpf_config)

        return mpf_config

    def _create_dmds(self, **kwargs):
        del kwargs
        self.create_dmds()
        self.create_rgb_dmds()
        self.events.remove_all_handlers_for_event("client_connected")

    def _load_font_paths(self):
        # Add local machine fonts path
        if os.path.isdir(os.path.join(self.machine_path,
                                      self.machine_config['mpf-mc']['paths']['fonts'])):

            resource_add_path(os.path.join(self.machine_path,
                                           self.machine_config['mpf-mc']['paths']['fonts']))

        # Add mpfmc fonts path
        resource_add_path(Path(mpfmc.__path__[0]) / 'fonts')

    def _initialize_sound_system(self):
        # Only initialize sound assets if sound system is loaded and enabled
        if self.sound_system is not None and self.sound_system.enabled:
            SoundAsset.extensions = tuple(
                self.sound_system.audio_interface.supported_extensions())
            SoundAsset.initialize(self)
        else:
            # If the sound system is not loaded or enabled, remove the
            # audio-related config_player modules and config collections
            del self.machine_config['mpf-mc']['config_players']['sound']
            del self.machine_config['mpf-mc']['config_players']['track']
            del self.machine_config['mpf-mc']['config_players']['sound_loop']
            del self.machine_config['mpf-mc']['config_players']['playlist']
            del self.machine_config['mpf-mc']['config_collections']['sound_loop_set']
            del self.machine_config['mpf-mc']['config_collections']['playlist']

    def get_system_config(self):
        return self.machine_config['mpf-mc']

    def validate_machine_config_section(self, section):
        """Validate machine config."""
        if section not in self.config_validator.get_config_spec():
            return

        if section not in self.machine_config:
            self.machine_config[section] = dict()

        self.machine_config[section] = self.config_validator.validate_config(
            section, self.machine_config[section], section)

    def get_config(self):
        return self.machine_config

    def _set_machine_path(self):
        self.log.debug("Machine path: %s", self.machine_path)

        # Add the machine folder to sys.path so we can import modules from it
        sys.path.insert(0, self.machine_path)

    def register_boot_hold(self, hold):
        # print('registering boot hold', hold)
        if self.is_init_done.is_set():
            raise AssertionError("Register hold after init_done")
        self._boot_holds.add(hold)

    def clear_boot_hold(self, hold):
        if self.is_init_done.is_set():
            raise AssertionError("Register hold after init_done")
        self._boot_holds.remove(hold)
        # print('clearing boot hold', hold, self._boot_holds)
        self.log.debug('Clearing boot hold %s. Holds remaining: %s', hold, self._boot_holds)
        if not self._boot_holds:
            self.init_done()

    def _register_config_players(self):
        # todo move this to config_player module

        for name, module in self.machine_config['mpf-mc'][
                'config_players'].items():
            imported_module = importlib.import_module(module)
            setattr(self, '{}_player'.format(name),
                    imported_module.McPlayerCls(self))

    def displays_initialized(self, *args):
        del args
        self.validate_machine_config_section('window')
        # pylint: disable-msg=import-outside-toplevel
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
        self.events.remove_all_handlers_for_event("displays_initialized")
        self._init()

    def create_dmds(self):
        """Create DMDs."""
        if 'dmds' in self.machine_config:
            for name, config in self.machine_config['dmds'].items():
                dmd = Dmd(self, name, config)
                self.dmds.append(dmd)

    def create_rgb_dmds(self):
        """Create RBG DMDs."""
        if 'rgb_dmds' in self.machine_config:
            for name, config in self.machine_config['rgb_dmds'].items():
                dmd = RgbDmd(self, name, config)
                self.rgb_dmds.append(dmd)

    def _init(self):
        # Since the window is so critical in Kivy, we can't continue the
        # boot process until the window is setup, and we can't set the
        # window up until the displays are initialized.

        self._load_named_colors()
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

        If you want to show slides that require images or video loaded from
        disk, use the event "init_done" instead which is posted once all the
        assets set to "preload" have been loaded.
        '''

        self.events.process_event_queue()
        self.events.post("init_phase_2")
        # no events docstring as this event is also in mpf
        self.events.process_event_queue()
        self.events.post("init_phase_3")
        # no events docstring as this event is also in mpf
        self.events.process_event_queue()
        self._load_custom_code()
        self.events.post("init_phase_4")
        # no events docstring as this event is also in mpf
        self.events.process_event_queue()
        self.events.post("init_phase_5")
        # no events docstring as this event is also in mpf
        self.events.process_event_queue()
        self.clear_boot_hold('init')
        self.events.remove_all_handlers_for_event("init_phase_1")
        self.events.remove_all_handlers_for_event("init_phase_2")
        self.events.remove_all_handlers_for_event("init_phase_3")
        self.events.remove_all_handlers_for_event("init_phase_4")
        self.events.remove_all_handlers_for_event("init_phase_5")

    def init_done(self):
        self.is_init_done.set()
        self.events.post("init_done")
        # no events docstring as this event is also in mpf
        self.events.process_event_queue()

    def build(self):
        self.start_time = time.time()
        self.ticks = 0
        self.clock.schedule_interval(self.tick, 0)
        self.events.add_handler("debug_dump_stats", self._debug_dump_displays)

    def _debug_dump_displays(self, **kwargs):
        del kwargs
        self.log.info("--- DEBUG DUMP DISPLAYS ---")
        self.log.info("Active slides: %s (Count: %s). Displays: %s (Count: %s). Available Slides: %s",
                      self.active_slides, len(self.active_slides), self.displays, len(self.displays), len(self.slides))
        for display in self.displays:
            self.log.info("Listing children for display: %s", display)
            children = 0
            for child in display.walk():
                self.log.info(child)
                children += 1
            self.log.info("Total children: %s", children)
        self.log.info("--- DEBUG DUMP DISPLAYS END ---")
        gc.collect()
        if not self.options["production"]:
            self.log.info("--- DEBUG DUMP OBJECTS ---")
            self.log.info("Elements in list (may be dead): %s", len(self.debug_refs))
            for element in self.debug_refs:
                real_element = element()
                if real_element:
                    self.log.info(real_element)
            self.log.info("--- DEBUG DUMP OBJECTS END ---")
        else:
            self.log.info("--- DEBUG DUMP OBJECTS DISABLED BECAUSE OF PRODUCTION FLAG ---")
        self.log.info("--- DEBUG DUMP CLOCK ---")
        ev = Clock._root_event  # pylint: disable-msg=protected-access
        while ev:
            self.log.info(ev)
            ev = ev.next
        self.log.info("--- DEBUG DUMP CLOCK END ---")

    def on_stop(self):
        self.log.info("Stopping...")
        self.thread_stopper.set()

        self.events.post("shutdown")
        self.events.process_event_queue()

        try:
            self.log.info("Loop rate %s Hz", round(self.ticks / (time.time() - self.start_time), 2))
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
        self.events.post('mc_reset_complete')
        '''event: mc_reset_complete
        desc: Posted on the MPF-MC only (e.g. not in MPF). This event is posted
        when the MPF-MC reset process is complete.
        '''

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
            player = Player(self, len(self.player_list))
            self.player_list.append(player)

            self.events.post('player_added', player=player, num=player_num)
            # no events docstring as this event is also in mpf

            # Enable player var events and send all initial values
            player.enable_events(True, True)

    def update_player_var(self, name, value, player_num):
        try:
            self.player_list[int(player_num) - 1][name] = value
        except (IndexError, KeyError):
            pass

    def player_start_turn(self, number, **kwargs):
        del kwargs
        if ((self.player and self.player.number != number) or
                not self.player):

            try:
                self.player = self.player_list[int(number) - 1]
                self.events.post('player_turn_start', number=number,
                                 player=self.player)
            except IndexError:
                self.log.error('Received player turn start for player %s, but '
                               'only %s player(s) exist',
                               number, len(self.player_list))

    def create_machine_var(self, name, value):
        """Same as set_machine_var."""
        self.set_machine_var(name, value)

    def set_machine_var(self, name, value):
        """Set machine var and send it via BCP to MPF."""
        if hasattr(self, "bcp_processor") and self.bcp_processor.connected:
            self.bcp_processor.send_machine_var_to_mpf(name, value)

    def receive_machine_var_update(self, name, value, change, prev_value):
        """Update a machine var received via BCP."""
        if value is None:
            try:
                del self.machine_vars[name]
            except KeyError:
                pass
        else:
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

    def tick(self, dt):
        """Process event queue."""
        del dt
        self.ticks += 1
        self.events.process_event_queue()

    def _load_custom_code(self):
        if 'mc_custom_code' in self.machine_config:
            self.log.debug("Loading custom_code...")

            for custom_code in Util.string_to_event_list(self.machine_config['mc_custom_code']):

                self.log.debug("Loading '%s' custom_code", custom_code)

                custom_code_obj = Util.string_to_class(custom_code)(
                    mc=self,
                    name=custom_code)

                self.custom_code.append(custom_code_obj)

    def _check_crash_queue(self, dt):
        del dt
        try:
            crash = self.crash_queue.get(block=False)
        except queue.Empty:
            pass
        else:
            self.log.critical("Shutting down due to child thread crash")
            self.log.critical("Crash details: %s", crash)
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

    def post_mc_native_event(self, event, **kwargs):
        if self.bcp_processor.enabled and self.bcp_client_connected:
            self.bcp_processor.send('trigger', name=event, **kwargs)

        self.events.post(event, **kwargs)
