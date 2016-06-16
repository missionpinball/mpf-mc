import logging
from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestAudioDisabled(MpfMcTestCase):
    """
    Tests the default audio settings (no 'sound_system' entries in the config file)
    """

    def get_machine_path(self):
        return 'tests/machine_files/audio'

    def get_config_file(self):
        return 'test_audio_disabled.yaml'

    def test_default_sound_system(self):
        """ Tests the sound system and audio interface with when the config settings
        disable the sound system. """

        if self.mc.sound_system is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system is not enabled - unable to run audio tests")
            return

        self.assertIsNotNone(self.mc.sound_system)
        self.assertIsNone(self.mc.sound_system.audio_interface)
