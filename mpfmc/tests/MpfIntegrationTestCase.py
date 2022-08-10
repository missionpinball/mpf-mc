import logging
import os
import sys

import mpf.core

os.environ['KIVY_NO_FILELOG'] = '1'
os.environ['KIVY_NO_CONSOLELOG'] = '1'
os.environ["KIVY_NO_ARGS"] = "1"

from queue import Queue

import time
from kivy.config import Config
from kivy.logger import Logger
from kivy.base import runTouchApp, EventLoop
from kivy.clock import Clock
from kivy.uix.widget import Widget as KivyWidget

for handler in Logger.handlers:
    Logger.removeHandler(handler)

sys.stderr = sys.__stderr__

import mpfmc
import mpfmc.core
from mpf.tests.MpfBcpTestCase import MockBcpClient
from mpf.tests.MpfTestCase import MpfTestCase, patch, UnitTestConfigLoader


class TestBcpClient(MockBcpClient):
    def __init__(self, machine, name, bcp):
        super().__init__(machine, name, bcp)
        self.queue = Queue()
        self.exit_on_close = False

        self.fps = 30

        self._start_time = time.time()
        Clock._start_tick = self._start_time
        Clock._last_tick = self._start_time
        Clock.time = self._mc_time
        Clock._events = [[] for i in range(256)]
        with patch("mpfmc.core.bcp_processor.BCPServer"):
            self._start_mc()
        self.mc_task = self.machine.clock.schedule_interval(self._run_mc, 1 / self.fps)

        bcp_mc = self.mc.bcp_processor
        bcp_mc.send = self.receive
        self.queue = bcp_mc.receive_queue
        self.mc.bcp_processor.enabled = True
        self.mc.bcp_client_connected = True
        self.mc.events.post("client_connected")

    def get_absolute_machine_path(self):
        # creates an absolute path based on machine_path
        return self.machine.machine_path

    def get_options(self):
        return dict(machine_path=self.get_absolute_machine_path(),
                    mcconfigfile='mcconfig.yaml',
                    production=False,
                    configfile=self.machine.options['configfile'],
                    no_load_cache=False,
                    create_config_cache=True,
                    bcp=False)

    def preprocess_config(self, config):
        # TODO this method is copied from the mc.py launcher. Prob a better way
        kivy_config = config['kivy_config']

        try:
            kivy_config['graphics'].update(config['displays']['window'])
        except KeyError:
            pass

        try:
            kivy_config['graphics'].update(config['window'])
        except KeyError:
            pass

        if 'top' in kivy_config['graphics'] and 'left' in kivy_config['graphics']:
            kivy_config['graphics']['position'] = 'custom'

        for section, settings in kivy_config.items():
            for k, v in settings.items():
                try:
                    if k in Config[section]:
                        Config.set(section, k, v)
                except KeyError:
                    continue

    def _start_app_as_worker(self):
        # from app::run
        if not self.mc.built:
            self.mc.load_config()
            self.mc.load_kv(filename=self.mc.kv_file)
            root = self.mc.build()
            if root:
                self.mc.root = root
        if self.mc.root:
            if not isinstance(self.mc.root, KivyWidget):
                Logger.critical('App.root must be an _instance_ of Kivy Widget')
                raise Exception('Invalid instance in App.root')
            from kivy.core.window import Window
            Window.add_widget(self.mc.root)

        # Check if the window is already created
        from kivy.base import EventLoop
        window = EventLoop.window
        if window:
            self.mc._app_window = window
            window.set_title(self.mc.get_application_name())
            icon = self.mc.get_application_icon()
            if icon:
                window.set_icon(icon)
            self.mc._install_settings_keys(window)
        else:
            Logger.critical("Application: No window is created."
                            " Terminating application run.")
            return

        self.mc.dispatch('on_start')
        runTouchApp(embedded=True)  # change is here

        while not self.mc.is_init_done.is_set():
            EventLoop.idle()

    def _start_mc(self):
        from mpfmc.core.mc import MpfMc

        # prevent sleep in clock
        Clock._max_fps = 0

        machine_path = self.get_absolute_machine_path()

        config_loader = UnitTestConfigLoader(machine_path, self.machine.options['configfile'], {}, {}, {})

        config = config_loader.load_mc_config()

        self.mc = MpfMc(config=config, options=self.get_options())

        from kivy.core.window import Window
        Window.create_window()
        Window.canvas.clear()

        self._start_app_as_worker()

    def _mc_time(self):
        return self._start_time + self.machine.clock.loop._time

    def _run_mc(self):
        EventLoop.idle()

    def stop(self):
        self.mc.stop()
        self.machine.clock.unschedule(self.mc_task)

    def send(self, bcp_command, kwargs):
        self.queue.put((bcp_command, kwargs))

    def receive(self, bcp_command, callback=None, rawbytes=None, **kwargs):
        if rawbytes:
            kwargs['rawbytes'] = rawbytes
        self.receive_queue.put_nowait((bcp_command, kwargs))

        if callback:
            callback()


class MpfIntegrationTestCase(MpfTestCase):

    fps = 30

    def get_use_bcp(self):
        return True

    def get_absolute_machine_path(self):
        # creates an absolute path based on machine_path
        return os.path.abspath(os.path.join(
            mpfmc.core.__path__[0], os.pardir, self.get_machine_path()))

    def get_enable_plugins(self):
        return True

    def mock_mc_event(self, event_name):
        """Configure an event to be mocked.

        Same as mock_event but for mc in integration test.
        """
        self._mc_events[event_name] = 0
        self.mc.events.remove_handler_by_event(event=event_name, handler=self._mock_mc_event_handler)
        self.mc.events.add_handler(event=event_name,
                                   handler=self._mock_mc_event_handler,
                                   event_name=event_name)

    def _mock_mc_event_handler(self, event_name, **kwargs):
        self._last_mc_event_kwargs[event_name] = kwargs
        self._mc_events[event_name] += 1

    def assertMcEventNotCalled(self, event_name):
        """Assert that event was not called.

        Same as mock_event but for mc in integration test.
        """
        if event_name not in self._mc_events:
            raise AssertionError("Event {} not mocked.".format(event_name))

        if self._mc_events[event_name] != 0:
            raise AssertionError("Event {} was called {} times.".format(event_name, self._mc_events[event_name]))

    def assertMcEventCalled(self, event_name, times=None):
        """Assert that event was called.

        Same as mock_event but for mc in integration test.
        """
        if event_name not in self._mc_events:
            raise AssertionError("Event {} not mocked.".format(event_name))

        if self._mc_events[event_name] == 0 and times != 0:
            raise AssertionError("Event {} was not called.".format(event_name))

        if times is not None and self._mc_events[event_name] != times:
            raise AssertionError("Event {} was called {} instead of {}.".format(
                event_name, self._mc_events[event_name], times))

    def __init__(self, methodName):
        super().__init__(methodName)
        self._mc_events = {}
        self._last_mc_event_kwargs = {}
        self.console_logger = None
        try:
            del self.machine_config_patches['mpf']['plugins']
        except KeyError:
            pass
        self.machine_config_patches['bcp'] = \
            {"connections": {"local_display": {"type": "mpfmc.tests.MpfIntegrationTestCase.TestBcpClient"}}}
        self.machine_config_patches['bcp']['servers'] = []
        self.expected_duration = 60

    def setUp(self):
        if self.unittest_verbosity() > 1:
            self.console_logger = logging.StreamHandler()
            self.console_logger.setLevel(logging.DEBUG)

            # set a format which is simpler for console use
            formatter = logging.Formatter('%(name)s: %(message)s')

            # tell the handler to use this format
            self.console_logger.setFormatter(formatter)

            # add the handler to the root logger
            logging.getLogger('').addHandler(self.console_logger)
        super().setUp()

        client = self.machine.bcp.transport.get_named_client("local_display")
        self.mc = client.mc
        self.advance_time_and_run()

    def tearDown(self):
        super().tearDown()
        EventLoop.close()

        if self.console_logger:
            logging.getLogger('').removeFilter(self.console_logger)
            self.console_logger = None
