"""Test high score mode."""
from mpfmc.tests.MpfSlideTestCase import MpfSlideTestCase

from mpfmc.tests.MpfIntegrationTestCase import MpfIntegrationTestCase


class TestDMDs(MpfIntegrationTestCase, MpfSlideTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'integration/machine_files/dmd/'

    def test_empty_name(self):
        default = self.machine.rgb_dmds["default"]
        grb = self.machine.rgb_dmds["grb_dmd"]
        self.advance_time_and_run(.1)
        self.assertEqual(bytearray([00] * 128 * 32 * 3), default.hw_device.data)
        self.assertEqual(bytearray([00] * 128 * 32 * 3), grb.hw_device.data)
        self.post_event("show_dmd_slide_1")
        self.advance_time_and_run(.1)
        self.assertEqual(bytearray([0x3, 0xe, 0x22] * 128 * 32), default.hw_device.data)
        self.assertEqual(bytearray([0xe, 0x3, 0x22] * 128 * 32), grb.hw_device.data)
