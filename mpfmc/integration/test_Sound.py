from mpfmc.tests.MpfIntegrationTestCase import MpfIntegrationTestCase


class TestSound(MpfIntegrationTestCase):

    def get_machine_path(self):
        return 'integration/machine_files/sound'

    def get_config_file(self):
        return 'config.yaml'

    def test_sound_player_with_conditionals(self):
        self.machine.variables.set_machine_var("factory_reset_current_selection", 1)
        self.mock_mc_event("sounds_play")
        self.advance_time_and_run(1)
        self.assertMcEventNotCalled("sounds_play")
        self.machine.variables.set_machine_var("factory_reset_current_selection", 2)
        self.advance_time_and_run(1)
        self.assertMcEventCalled("sounds_play")
