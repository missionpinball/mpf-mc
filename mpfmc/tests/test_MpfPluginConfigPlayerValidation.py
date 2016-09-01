# This test is a bit unique because it's in the MPF-MC package but it runs on
# the MPF side of things, and therefore it uses MPF's test case instead of
# MPF-MC's.

import logging
import os
import time
from unittest.mock import *

from mpf.tests.loop import TimeTravelLoop, TestClock

import mpfmc
from mpf.tests.MpfTestCase import MpfTestCase, TestMachineController
import mpf.core
from mpf.core.config_validator import ConfigValidator


class TestMpfPluginConfigPlayerValidation(MpfTestCase):

    # todo maybe make a base class to run MPF tests from MPFMC?
    # see comments for changes from base class

    def setUp(self):
        # we want to reuse config_specs to speed tests up
        ConfigValidator.unload_config_spec = MagicMock()

        self._events = {}

        # print(threading.active_count())

        self.test_start_time = time.time()
        if self.unittest_verbosity() > 1:
            logging.basicConfig(level=logging.DEBUG,
                                format='%(asctime)s : %(levelname)s : %('
                                       'name)s : %(message)s')
        else:
            # no logging by default
            logging.basicConfig(level=99)

        self.save_and_prepare_sys_path()

        # init machine
        machine_path = os.path.abspath(os.path.join(
            mpfmc.__path__[0], os.pardir, 'mpfmc', self.getMachinePath()))

        try:
            self.loop = TimeTravelLoop()
            self.clock = TestClock(self.loop)
            # Note the 'True' for enabling plugins, change from base
            self.machine = TestMachineController(
                os.path.abspath(os.path.join(
                    mpf.core.__path__[0], os.pardir)), machine_path,
                self.getOptions(),
                self.machine_config_patches, self.clock, {}, True)

            while not self.machine.test_init_complete:
                self.advance_time_and_run(0.01)

            self.machine.ball_controller.num_balls_known = 99
            self.advance_time_and_run(300)

        except Exception as e:
            # todo temp until I can figure out how to stop the asset loader
            # thread automatically.
            try:
                self.machine.stop()
            except AttributeError:
                pass
            raise e

        # remove config patches
        self.machine_config_patches = dict()
        # use bcp mock
        self.machine_config_patches['bcp'] = \
            {"connections": {"local_display": {"type": "mpf.tests.MpfTestCase.MockBcpClient"}}}

    def getConfigFile(self):
        return 'mpf_plugin_validation.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/mpf_plugin_config_player_validation/'

    def test_slides_validation_shows(self):

        # for step in self.machine.shows['show1'].show_steps:
        #     print(step)
        #     print()

        self.assertIn('show1', self.machine.shows)

        step_0 = self.machine.shows['show1'].show_steps[0]['slides']['slide1']

        self.assertIn('widgets', step_0)
        self.assertEqual(1, len(step_0['widgets']))
        self.assertEqual('text', step_0['widgets'][0]['type'])
        self.assertEqual('TEST 1', step_0['widgets'][0]['text'])
        self.assertEqual([1.0, 0, 0, 1.0], step_0['widgets'][0]['color'])
        self.assertEqual(100, step_0['widgets'][0]['font_size'])

        self.machine.events.post('event1')
        self.advance_time_and_run(4)

        # for command in self.sent_bcp_commands:
        #     print()
        #     print(command)
