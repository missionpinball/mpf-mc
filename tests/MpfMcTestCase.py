import sys

sys.path.insert(0, '../mpf')  # temp until we get a proper install for mpf

import unittest
from kivy.clock import Clock
from kivy.config import Config
from mpf.system.config import Config as MpfConfig
from mpf.system.utility_functions import Util

Config.set('kivy', 'log_enable', '0')
Config.set('kivy', 'log_level', 'warning')

from mc.core.mc import MpfMc


class TestMpfMc(MpfMc):
    pass


class MpfMcTestCase(unittest.TestCase):
    mc = None

    def get_options(self):

        return dict(machine_path=self.get_machine_path(),
                    mcconfigfile='mc/mcconfig.yaml',
                    configfile=Util.string_to_list(self.get_config_file()))

    def get_machine_path(self):
        return 'tests/machine_files/mpf-mc'

    def get_config_file(self):
        return 'test_mc.yaml'

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

    def on_window_flip(self, window):
        print('flip', self.mc.default_display.size)

    def tearDown(self):
        from kivy.base import stopTouchApp
        from kivy.core.window import Window
        Window.unbind(on_flip=self.on_window_flip)
        stopTouchApp()

    def run(self, name):
        self._test_name = name
        mpf_config = MpfConfig.load_config_file(self.get_options()[
                                                    'mcconfigfile'])
        mpf_config = MpfConfig.load_machine_config(
                Util.string_to_list(self.get_config_file()),
                self.get_machine_path(),
                mpf_config['mpf-mc']['paths']['config'], mpf_config)
        self.preprocess_config(mpf_config)

        self.mc = TestMpfMc(options=self.get_options(),
                            config=mpf_config,
                            machine_path=self.get_machine_path())

        from kivy.core.window import Window
        Window.bind(on_flip=self.on_window_flip)
        Window.create_window()
        Window.canvas.clear()

        Clock.schedule_once(self.run_test, 1)
        return self.mc.run()

    def run_test(self, time):
        return super().run(self._test_name)
