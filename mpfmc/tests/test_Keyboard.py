from mpfmc.tests.MpfMcTestCase import MpfMcTestCase
from unittest.mock import MagicMock


class TestKeyboard(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/keyboard'

    def get_config_file(self):
        return 'test_keyboard.yaml'

    def press(self, key_string, mods=None):
        if mods:
            if not isinstance(mods, list):
                mods = [mods]
        else:
            mods = list()

        self.mc.keyboard._on_keyboard_down(None, (None, key_string.lower()),
                                           None,
                                           mods)
        # self.advance_time()

    def release(self, key_string):
        self.mc.keyboard._on_keyboard_up(None, (None, key_string.lower()))
        # self.advance_time()

    def test_switch(self):
        self.press('a')
        bcp_command = ('switch', None, {'name': 'switch_a', 'state': 1})
        self.assertIn(bcp_command, self.sent_bcp_commands)

        self.release('a')
        bcp_command = ('switch', None, {'name': 'switch_a', 'state': 0})
        self.assertIn(bcp_command, self.sent_bcp_commands)

        self.sent_bcp_commands = list()

        # When a key is held down, kivy keeps firing the same event over and
        # over each frame, so make sure that we only send one event
        self.press('a')
        self.assertEqual(len(self.sent_bcp_commands), 1)

        self.press('a')
        self.press('a')
        self.press('a')
        self.press('a')
        self.press('a')
        self.press('a')
        self.assertEqual(len(self.sent_bcp_commands), 1)

    def test_toggle_switch(self):
        # BCP spec sends state -1 to tell MPF to flip the switch state. -1 is
        # used so mpf-mc doesn't have to maintain of state which means it can't
        # get out of sync. :)
        self.press('b')
        bcp_command = ('switch', None, {'name': 'switch_b', 'state': -1})
        self.assertIn(bcp_command, self.sent_bcp_commands)

        self.release('b')

        # make sure releasing doesn't send it again
        found = 0
        for x in self.sent_bcp_commands:
            if x == ('switch', None, {'name': 'switch_b', 'state': -1}):
                found += 1

        self.assertEqual(found, 1)

    def test_inverted_switch(self):
        self.press('c')
        bcp_command = ('switch', None, {'name': 'switch_c', 'state': 0})
        self.assertIn(bcp_command, self.sent_bcp_commands)

        self.release('c')
        bcp_command = ('switch', None, {'name': 'switch_c', 'state': 1})
        self.assertIn(bcp_command, self.sent_bcp_commands)

    def test_mpf_event(self):
        self.mc.bcp_processor.enabled = True

        self.press('d')

        bcp_command = ('trigger', None, {'name': 'event_d'})
        self.assertIn(bcp_command, self.sent_bcp_commands)

    def test_mpf_event_with_params(self):
        self.mc.bcp_processor.enabled = True

        self.press('e')

        bcp_command = ('trigger', None, {'mission': 'pinball', 'foo': 'bar',
                                         'name': 'event_e'})
        self.assertIn(bcp_command, self.sent_bcp_commands)

    def test_mc_event(self):
        self.callback = MagicMock()

        self.mc.events.add_handler('event_f', self.callback)

        self.press('f')
        self.advance_time()
        self.callback.assert_called_once_with()

    def test_mc_event_with_params(self):
        self.callback = MagicMock()

        self.mc.events.add_handler('event_g', self.callback)

        self.press('g')
        self.advance_time()
        self.callback.assert_called_once_with(foo='bar', mission='pinball')

    def test_mod_key_with_dash(self):
        self.press('a', 'shift')

        bcp_command = ('switch', None, {'name': 'shift_a', 'state': 1})
        self.assertIn(bcp_command, self.sent_bcp_commands)

    def test_mod_key_with_plus(self):
        self.press('b', 'shift')

        bcp_command = ('switch', None, {'name': 'shift_b', 'state': 1})
        self.assertIn(bcp_command, self.sent_bcp_commands)

    def test_multiple_mod_keys(self):
        self.press('c', ['shift', 'ctrl'])
        self.release('c')

        bcp_command = ('switch', None, {'name': 'shift_ctrl_c', 'state': 1})
        self.assertIn(bcp_command, self.sent_bcp_commands)

        self.sent_bcp_commands = list()

        # swap the order of the mod keys
        self.press('c', ['ctrl', 'shift'])

        bcp_command = ('switch', None, {'name': 'shift_ctrl_c', 'state': 1})
        self.assertIn(bcp_command, self.sent_bcp_commands)

    def test_number_key(self):
        self.press('1')
        bcp_command = ('switch', None, {'name': 'switch_1', 'state': 1})
        self.assertIn(bcp_command, self.sent_bcp_commands)

    def test_period(self):
        self.press('.')
        bcp_command = ('switch', None, {'name': 'switch_period', 'state': 1})
        self.assertIn(bcp_command, self.sent_bcp_commands)

    def test_slash(self):
        self.press('/')
        bcp_command = ('switch', None, {'name': 'switch_slash', 'state': 1})
        self.assertIn(bcp_command, self.sent_bcp_commands)
