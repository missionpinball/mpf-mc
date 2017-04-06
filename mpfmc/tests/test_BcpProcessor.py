from unittest.mock import MagicMock

from mpfmc._version import __version__
from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestBcpProcessor(MpfMcTestCase):

    def __init__(self, *args):
        super().__init__(*args)

    def get_machine_path(self):
        return 'tests/machine_files/bcp'

    def get_config_file(self):
        return 'test_bcp_processor.yaml'

    def test_game_flow(self):
        self.send('hello',
                  version='1.1',
                  controller_version=__version__,
                  controller_name='Mission Pinball Framework')
        self.advance_time()

        response = ('hello', None, {'version': '1.1'})
        self.assertIn(response, self.sent_bcp_commands)

        self.send('mode_start',
                  name='tilt',
                  priority='10000')
        self.advance_time()
        self.send('mode_start',
                  name='attract',
                  priority='10')
        self.advance_time()

        self.send('mode_start',
                  name='game',
                  priority='20')
        self.advance_time()

        self.send('player_added',
                  player_num='1')
        self.advance_time()

        self.send('player_score',
                  value='0',
                  player_num='1',
                  prev_value='0',
                  change='False')
        self.advance_time()

        self.send('player_turn_start',
                  player_num='1')
        self.advance_time()

        self.send('player_variable',
                  name='ball',
                  value='1',
                  player_num='1',
                  prev_value='0',
                  change='True')
        self.advance_time()

        self.send('mode_stop',
                  name='attract')
        self.advance_time()

    def test_machine_variable(self):
        self.send('machine_variable',
                  value='FREE PLAY',
                  name='credits_string')
        self.assertEqual(self.mc.machine_vars['credits_string'], 'FREE PLAY')

        self.callback = MagicMock()
        self.mc.events.add_handler('machine_var_foo', self.callback)

        self.send('machine_variable',
                  value='0',
                  name='foo')
        self.assertEqual(self.mc.machine_vars['foo'], '0')
        self.advance_time()
        self.callback.assert_called_with(value='0', prev_value=None,
                                         change=True)

        self.callback.reset_mock()
        self.send('machine_variable',
                  value='10',
                  name='foo',
                  prev_value='0',
                  change='10')
        self.assertEqual(self.mc.machine_vars['foo'], '10')
        self.advance_time()
        self.callback.assert_called_with(value='10', prev_value='0',
                                         change='10')
