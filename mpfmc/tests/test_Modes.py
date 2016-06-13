from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestModes(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/modes'

    def get_config_file(self):
        return 'test_modes.yaml'

    def test_mc_mode_start(self):
        # this tests that the mode is read properly from the config too
        self.send(bcp_command='mode_start', name='mode1', priority=300)
        self.assertTrue(self.mc.modes['mode1'].active)
        self.assertEqual(self.mc.modes['mode1'].priority, 300)

        # try to start the mode again and make sure it doesn't explode
        self.send(bcp_command='mode_start', name='mode1')

        # stop the mode
        self.send(bcp_command='mode_stop', name='mode1')
        self.assertFalse(self.mc.modes['mode1'].active)
