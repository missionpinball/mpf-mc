import os
import sys
import unittest

os.environ['KIVY_NO_FILELOG'] = '1'
os.environ['KIVY_NO_CONSOLELOG'] = '1'

from kivy.graphics.opengl import glReadPixels, GL_RGB, GL_UNSIGNED_BYTE
from kivy import Config, Logger
from kivy.base import runTouchApp, stopTouchApp, EventLoop
from kivy.clock import Clock
from kivy.uix.widget import Widget

import mpfmc
from mpf.core.config_processor import ConfigProcessor
from mpf.core.utility_functions import Util
from mpfmc.core.utils import load_machine_config

Config.set('kivy', 'log_enable', '0')
Config.set('kivy', 'log_level', 'warning')


from mpfmc.core.mc import MpfMc
from time import time, sleep

sys.stderr = sys.__stderr__


class MpfMcTestCase(unittest.TestCase):
    def __init__(self, *args):
        self.sent_bcp_commands = list()
        super().__init__(*args)

        self._events = dict()
        self._last_event_kwargs = dict()
        self.max_test_setup_secs = 30

        self._fps = 30

    def _mc_time(self):
        return self._current_time

    def get_options(self):
        return dict(machine_path=self.get_machine_path(),
                    mcconfigfile='mpfmc/mcconfig.yaml',
                    configfile=Util.string_to_list(self.get_config_file()),
                    bcp=False)

    def getAbsoluteMachinePath(self):
        return os.path.abspath(os.path.join(
            mpfmc.__path__[0], os.pardir, 'mpfmc', self.get_machine_path()))

    def get_machine_path(self):
        raise NotImplementedError

    def get_config_file(self):
        raise NotImplementedError

    def get_abs_path(self, path):
        return os.path.join(os.path.abspath(os.curdir), path)

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

        if 'top' in kivy_config['graphics'] and 'left' in kivy_config[
            'graphics']:
            kivy_config['graphics']['position'] = 'custom'

        for section, settings in kivy_config.items():
            for k, v in settings.items():
                try:
                    if k in Config[section]:
                        Config.set(section, k, v)
                except KeyError:
                    continue

    def advance_time(self, secs=.1):
        start = self._current_time
        while self._current_time < start + secs:
            EventLoop.idle()
            self._current_time += 1 / self._fps

    def advance_real_time(self, secs=.1):
        start = self._current_time
        while self._current_time < start + secs:
            EventLoop.idle()
            sleep(1 / self._fps)
            self._current_time += 1 / self._fps

        EventLoop.idle()

    def get_pixel_color(self, x, y):
        """Returns a binary string of the RGB bytes that make up the slide
        pixel at the passed x,y coordinates. 2 bytes per pixel, 6 bytes total.
        This method *does* compensate for different window sizes.

        Note: This method does not work yet.

        """
        raise NotImplementedError  # remove when we fix it. :)

        # do the Window import here because we don't want to import it at the
        # top or else we won't be able to set window properties
        from kivy.core.window import Window

        # convert the passed x/y to the actual x/y of the Window since it's
        # possible for the mpf-mc display size to be different than the Window
        # size
        x *= Window.width / Window.children[0].width
        y *= Window.height / Window.children[0].height

        return glReadPixels(x, y, 1, 1, GL_RGB, GL_UNSIGNED_BYTE)

    def tearDown(self):
        self.mc.stop()

    def patch_bcp(self):
        # used internally
        self.orig_bcp_send = self.mc.bcp_processor.send
        self.mc.bcp_processor.send = self._bcp_send

        # this is used to send BCP commands to mpf-mc
        self.send = self.mc.bcp_processor._process_command

        self.mc.bcp_client_connected = True

    def _bcp_send(self, bcp_command, callback=None, **kwargs):
        # used for commands sent from the MC to the PC
        # print((bcp_command, callback, kwargs))
        self.sent_bcp_commands.append((bcp_command, callback, kwargs))
        self.orig_bcp_send(bcp_command=bcp_command, callback=callback,
                           **kwargs)

    def setUp(self):
        # Most of the setup is done in run(). Explanation is there.
        Config._named_configs.pop('app', None)

        self._start_time = time()
        self._current_time = self._start_time
        Clock._start_tick = self._start_time
        Clock._last_tick = self._start_time
        Clock.time = self._mc_time

        # prevent sleep in clock
        Clock._max_fps = 0
        Clock._events = [[] for i in range(256)]
        self._test_started = self._start_time

        from mpf.core.player import Player
        Player.monitor_enabled = False

        mpf_config = ConfigProcessor.load_config_file(os.path.abspath(
            os.path.join(mpfmc.__path__[0], os.pardir,
                         self.get_options()['mcconfigfile'])), 'machine')

        machine_path = self.getAbsoluteMachinePath()

        mpf_config = load_machine_config(
                Util.string_to_list(self.get_config_file()),
                machine_path,
                mpf_config['mpf-mc']['paths']['config'], mpf_config)
        self.preprocess_config(mpf_config)

        self.mc = MpfMc(options=self.get_options(),
                        config=mpf_config,
                        machine_path=machine_path)

        self.patch_bcp()

        from kivy.core.window import Window
        Window.create_window()
        Window.canvas.clear()

        self._start_app_as_slave()

    def _start_app_as_slave(self):
        # from app::run
        if not self.mc.built:
            self.mc.load_config()
            self.mc.load_kv(filename=self.mc.kv_file)
            root = self.mc.build()
            if root:
                self.mc.root = root
        if self.mc.root:
            if not isinstance(self.mc.root, Widget):
                Logger.critical('App.root must be an _instance_ of Widget')
                raise Exception('Invalid instance in App.root')
            from kivy.core.window import Window
            Window.add_widget(self.mc.root)

        # Check if the window is already created
        from kivy.base import EventLoop
        window = EventLoop.window
        if window:
            self.mc._app_window = window
            #window.set_title(self.mc.get_application_name() + self._testMethodName)
            icon = self.mc.get_application_icon()
            if icon:
                window.set_icon(icon)
            self.mc._install_settings_keys(window)
        else:
            Logger.critical("Application: No window is created."
                            " Terminating application run.")
            return

        self.mc.dispatch('on_start')
        runTouchApp(slave=True)  # change is here

        while not self.mc.is_init_done.is_set():
            EventLoop.idle()

        # set a nice title
        window.set_title(self.__class__.__name__ + "::" + self._testMethodName)

    def dump_clock(self):
        print("---------")
        events = []
        for slot in Clock._events:
            for event in slot:
                events.append(event)

        events.sort(key=lambda x: str(x.get_callback()))

        for event in events:
            print(event.get_callback(), event.timeout)

    def _mock_event_handler(self, event_name, **kwargs):
        self._last_event_kwargs[event_name] = kwargs
        self._events[event_name] += 1

    def mock_event(self, event_name):
        self._events[event_name] = 0
        self.mc.events.remove_handler_by_event(
            event=event_name, handler=self._mock_event_handler)
        self.mc.events.add_handler(event=event_name,
                                   handler=self._mock_event_handler,
                                   event_name=event_name)

    def assertEventNotCalled(self, event_name):
        """Assert that event was not called."""
        if event_name not in self._events:
            raise AssertionError("Event {} not mocked.".format(event_name))

        if self._events[event_name] != 0:
            raise AssertionError("Event {} was called {} times.".format(
                event_name, self._events[event_name]))

    def assertEventCalled(self, event_name, times=None):
        """Assert that event was called."""
        if event_name not in self._events:
            raise AssertionError("Event {} not mocked.".format(event_name))

        if self._events[event_name] == 0:
            raise AssertionError("Event {} was not called.".format(event_name))

        if times is not None and self._events[event_name] != times:
            raise AssertionError("Event {} was called {} instead of {}.".format(
                event_name, self._events[event_name], times))

    def assertEventCalledWith(self, event_name, **kwargs):
        """Assert that event was called with kwargs."""
        self.assertEventCalled(event_name)
        self.assertEqual(kwargs, self._last_event_kwargs[event_name],
                         "Args for {} differ.".format(event_name))

    def reset_mock_events(self):
        for event in self._events.keys():
            self._events[event] = 0
