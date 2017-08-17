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
            self.skipTest("Sound system is not enabled")

        self.assertIsNotNone(self.mc.sound_system)

        if self.mc.sound_system.audio_interface is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system audio interface could not be loaded - skipping audio tests")
            self.skipTest("Sound system audio interface could not be loaded")

        self.assertIsNone(self.mc.sound_system.audio_interface)
