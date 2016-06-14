import os
import sys
import unittest

os.environ['KIVY_NO_FILELOG'] = '1'
os.environ['KIVY_NO_CONSOLELOG'] = '1'

from kivy.base import EventLoop, stopTouchApp
from kivy.clock import Clock
from kivy.config import Config
from kivy.graphics.opengl import glReadPixels, GL_RGB, GL_UNSIGNED_BYTE

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

    def get_options(self):
        return dict(machine_path=self.get_machine_path(),
                    mcconfigfile='mpfmc/mcconfig.yaml',
                    configfile=Util.string_to_list(self.get_config_file()),
                    bcp=False)

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
        start = time()
        self.mc.events.process_event_queue()
        while time() < start + secs:
            sleep(.01)
            self.mc.events.process_event_queue()
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

    def setUp(self):
        # Most of the setup is done in run(). Explanation is there.
        Config._named_configs.pop('app', None)

    def tearDown(self):
        stopTouchApp()

    def patch_bcp(self):
        # used internally
        self.orig_bcp_send = self.mc.bcp_processor.send
        self.mc.bcp_processor.send = self._bcp_send

        # this is used to send BCP commands to mpf-mc
        self.send = self.mc.bcp_processor._process_command

    def _bcp_send(self, bcp_command, callback=None, **kwargs):
        # used for commands sent from the MC to the PC
        # print((bcp_command, callback, kwargs))
        self.sent_bcp_commands.append((bcp_command, callback, kwargs))
        self.orig_bcp_send(bcp_command=bcp_command, callback=callback,
                           **kwargs)

    def run(self, name):
        self._test_name = self.id()
        self._test = name
        # This setup is done in run() because we need to give control to the
        # kivy event loop which we can only do by returning from the run()
        # that's called. So we override run() and setup mpf-mc and then call
        # our own run_test() on a callback. Then we can wait until the
        # environment is setup (which can take a few frames), then we call
        # super().run() to get the actual TestCase.run() method to run and
        # we return the results.

        # We have to do this in run() and not setUp() because run actually
        # calls setUp(), so since we were overriding it ours doesn't call it
        # so we just do our setup here since if we manually called setUp() then
        # it would be called again when we call super().run().

        from mpf.core.player import Player
        Player.monitor_enabled = False

        mpf_config = ConfigProcessor.load_config_file(os.path.abspath(
            os.path.join(mpfmc.__path__[0], os.pardir,
                         self.get_options()['mcconfigfile'])), 'machine')

        machine_path = os.path.abspath(os.path.join(
            mpfmc.__path__[0], os.pardir, 'mpfmc', self.get_machine_path()))

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

        Clock.schedule_once(self.run_test, 0)
        self.mc.run()

    def run_test(self, time):
        # set the title bar, just for fun. :)
        self.mc.title = str(self._test_name)

        if not self.mc.is_init_done:
            Clock.schedule_once(self.run_test, 0)
            return

        return super().run(self._test)
