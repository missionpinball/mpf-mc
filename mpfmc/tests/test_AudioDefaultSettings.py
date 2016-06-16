import logging
from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestAudioDefaultSettings(MpfMcTestCase):
    """
    Tests the default audio settings (no 'sound_system' entries in the config file)
    """

    def get_machine_path(self):
        return 'tests/machine_files/audio'

    def get_config_file(self):
        return 'test_audio_default_settings.yaml'

    def test_default_sound_system(self):
        """ Tests the sound system and audio interface with default settings """

        if self.mc.sound_system is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system is not enabled - unable to run audio tests")
            return

        self.assertIsNotNone(self.mc.sound_system)
        self.assertIsNotNone(self.mc.sound_system.audio_interface)
        settings = self.mc.sound_system.audio_interface.get_settings()
        self.assertIsNotNone(settings)
        self.assertEqual(settings['buffer_samples'], 2048)
        self.assertEqual(settings['audio_channels'], 1)
        self.assertEqual(settings['sample_rate'], 44100)
