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

    def get_absolute_machine_path(self):
        return os.path.abspath(os.path.join(
            mpfmc.__path__[0], os.pardir, 'mpfmc', self.get_machine_path()))

    def get_enable_plugins(self):
        return True

    def get_config_file(self):
        return 'mpf_plugin_validation.yaml'

    def get_machine_path(self):
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
