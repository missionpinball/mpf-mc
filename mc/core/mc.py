"""Contains the MpfMc base class, which is the main App instance for the
mpf-mc.

"""
import queue
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.logger import Logger
from mc.core.bcp_processor import BcpProcessor

from mc.core.config_processor import McConfig
from mc.core.mode_controller import ModeController
from mc.core.slide_player import SlidePlayer
from mc.core.widget_player import WidgetPlayer
from mpf.system.config import CaseInsensitiveDict
from mpf.system.events import EventManager
from mpf.system.player import Player


class MpfMc(App):
    def __init__(self, options, config, machine_path, **kwargs):
        super().__init__(**kwargs)

        self.options = options

        self.machine_config = config
        self.machine_path = machine_path
        self.modes = CaseInsensitiveDict()
        self.player_list = list()
        self.player = None
        self.num_players = 0

        self.slide_configs = dict()

        self.displays = CaseInsensitiveDict()

        self.machine_vars = CaseInsensitiveDict()
        self.machine_var_monitor = False
        self.targets = dict()
        """Dict which contains all the active slide frames in the machine that
        a slide can target. Will always contain an entry called 'default'
        which will be used if a slide doesn't specify targeting.
        """

        self.events = EventManager(self, setup_event_player=False)
        self.mode_controller = ModeController(self)
        McConfig.load_config_spec()
        self.config_processor = McConfig(self)
        self.slide_player = SlidePlayer(self)
        self.widget_player = WidgetPlayer(self)
        self.keyboard = None
        self.crash_queue = queue.Queue()
        self.ticks = 0
        self.start_time = 0
        self.crash_queue = None
        self.init_done = False

        self.bcp_processor = BcpProcessor(self)

    def validate_machine_config_section(self, section):
        if section not in McConfig.config_spec:
            return

        if section not in self.machine_config:
            self.config[section] = dict()

        self.machine_config[section] = self.config_processor.process_config2(
                section, self.machine_config[section], section)

    def get_config(self):
        return self.machine_config

    def displays_initialized(self, *args):
        print('Displays Initialized')
        from mc.uix.window import Window
        Window.initialize(self)

        self.events.post("init_phase_1")
        self.events._process_event_queue()
        self.events.post("init_phase_2")
        self.events._process_event_queue()
        self.events.post("init_phase_3")
        self.events._process_event_queue()
        self.events.post("init_phase_4")
        self.events._process_event_queue()
        self.events.post("init_phase_5")
        self.events._process_event_queue()
        McConfig.unload_config_spec()
        self.reset()

        self.init_done = True

    def build(self):
        self.start_time = time.time()
        self.ticks = 0
        Clock.schedule_interval(self.tick, 0)

    def on_stop(self):
        try:
            print("loop rate {}Hz".format(
                    round(self.ticks / (time.time() - self.start_time), 2)))
        except ZeroDivisionError:
            pass

        print("stopping...")

        try:
            self.bcp_processor.socket_thread.stop()
        except AttributeError:  # if we're running without BCP processor
            pass

    def reset(self, **kwargs):
        self.player = None
        self.player_list = list()

        self.events.add_handler('assets_to_load',
                                self._bcp_client_asset_loader_tick)

        # temp todo
        # self.events.replace_handler('timer_tick', self.asset_loading_counter)

        self.events.post('mc_reset_phase_1')
        self.events._process_event_queue()
        self.events.post('mc_reset_phase_2')
        self.events._process_event_queue()
        self.events.post('mc_reset_phase_3')
        self.events._process_event_queue()

    def game_start(self, **kargs):
        self.player = None
        self.player_list = list()
        self.num_players = 0
        self.events.post('game_started', **kargs)

    def game_end(self, **kwargs):
        self.player = None
        self.events.post('game_ended', **kwargs)

    def add_player(self, player_num):
        if player_num > len(self.player_list):
            Player(self, self.player_list)

            self.events.post('player_add_success', num=player_num)

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
            except IndexError:
                Logger.error('Received player turn start for player %s, but '
                             'only %s player(s) exist',
                             player_num, len(self.player_list))

    def _bcp_client_asset_loader_tick(self, total, remaining):
        self._pc_assets_to_load = int(remaining)
        self._pc_total_assets = int(total)

    # def asset_loading_counter(self):
    #
    #     if self.tick_num % 5 != 0:
    #         return
    #
    #     if AssetManager.total_assets or self._pc_total_assets:
    #         # max because this could go negative at first
    #         percent = max(0, int(float(AssetManager.total_assets -
    #                                    self._pc_assets_to_load -
    #                                    AssetManager.loader_queue.qsize()) /
    #                                    AssetManager.total_assets * 100))
    #     else:
    #         percent = 100
    #
    #     Logger.debug("Asset Loading Counter. PC remaining:{}, MC remaining:"
    #                    "{}, Percent Complete: {}".format(
    #                    self._pc_assets_to_load,
    # AssetManager.loader_queue.qsize(),
    #                    percent))
    #
    #     self.events.post('asset_loader',
    #                      total=AssetManager.loader_queue.qsize() +
    #                            self._pc_assets_to_load,
    #                      pc=self._pc_assets_to_load,
    #                      mc=AssetManager.loader_queue.qsize(),
    #                      percent=percent)
    #
    #     if not AssetManager.loader_queue.qsize():
    #
    #     if True:
    #
    #         if not self.pc_connected:
    #             self.events.post("waiting_for_client_connection")
    #             self.events.remove_handler(self.asset_loading_counter)
    #
    #         elif not self._pc_assets_to_load:
    #             Logger.debug("Asset Loading Complete")
    #             self.events.post("asset_loading_complete")
    #             self.bcp_processor.send('reset_complete')
    #
    #             self.events.remove_handler(self.asset_loading_counter)

    def set_machine_var(self, name, value, change, prev_value):

        if type(change) is not bool and change.lower() in ('false', '0'):
            change = False

        self.machine_vars[name] = value

        if change:
            Logger.debug("Setting machine_var '%s' to: %s, (prior: %s, "
                         "change: %s)", name, value, prev_value,
                         change)
            self.events.post('machine_var_' + name,
                             value=value,
                             prev_value=prev_value,
                             change=change)

        if self.machine_var_monitor:
            for callback in self.monitors['machine_var']:
                callback(name=name, value=self.vars[name],
                         prev_value=prev_value, change=change)

    def tick(self, time):
        self.events.post('timer_tick')
        self.ticks += 1
        self.events._process_event_queue()
