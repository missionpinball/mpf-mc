from mpfmc.tests.MpfIntegrationTestCase import MpfIntegrationTestCase
from mpfmc._version import version, extended_version


class TestBasicGame(MpfIntegrationTestCase):
    """Tests that MPF MC gets the basic stuff it needs from BCP from MPF.

    This includes players, games, modes, machine vars, player vars, etc.

    """

    def get_config_file(self):
        return 'basic_game.yaml'

    def get_machine_path(self):
        return 'integration/machine_files/basic_game/'

    def test_basic_game(self):
        self.hit_switch_and_run('drain', 1)
        self.hit_and_release_switch('start')
        self.mock_event("player_added")
        self.mock_mc_event("player_added")
        self.advance_time_and_run(1)

        # make sure the MPF side has everything
        self.assertModeRunning('game')
        self.assertTrue(self.machine.game.player)
        self.assertEqual(self.machine.game.player.ball, 1)
        self.assertEqual({'value': 'FREE PLAY', 'persist': False, 'expire_secs': None},
                         self.machine.variables.machine_vars['credits_string'])

        # make sure the MC side has everything
        self.assertTrue(self.mc.modes['game'].active)
        self.assertTrue(self.mc.player)
        self.assertEqual(self.mc.player.ball, 1)
        self.assertEqual('FREE PLAY', self.mc.machine_vars['credits_string'])

        self.assertEventCalled("player_added", 1)
        self.assertMcEventCalled("player_added", 1)

        self.assertMachineVarEqual(version, "mc_version")
        self.assertMachineVarEqual(extended_version, "mc_extended_version")
