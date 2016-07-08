import logging
from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestAudioBadBufferSetting(MpfMcTestCase):
    """
    Tests the audio settings with a bad buffer setting (not a power of two)
    """

    def get_machine_path(self):
        return 'tests/machine_files/audio'

    def get_config_file(self):
        return 'test_audio_bad_buffer_setting.yaml'

    def test_default_sound_system(self):
        """ Tests the sound system and audio interface with default settings """

        if self.mc.sound_system is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system is not enabled - unable to run audio tests")
            self.skipTest("Sound system is not enabled - unable to run audio tests")
            return

        logging.getLogger('TestAudio').setLevel(10)

        self.assertIsNotNone(self.mc.sound_system)
        self.assertIsNotNone(self.mc.sound_system.audio_interface)
        settings = self.mc.sound_system.audio_interface.get_settings()
        self.assertIsNotNone(settings)
        self.assertEqual(settings['buffer_samples'], 2048)
        self.assertEqual(settings['audio_channels'], 1)
        self.assertEqual(settings['sample_rate'], 44100)
