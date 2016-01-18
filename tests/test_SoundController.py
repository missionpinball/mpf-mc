from tests.MpfMcTestCase import MpfMcTestCase
from mc.core.sound import SoundController


class TestSoundController(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/sound_controller'

    def get_config_file(self):
        return 'test_sound_controller.yaml'

    def test_test(self):
        pass
