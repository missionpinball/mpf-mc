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

        logging.getLogger('TestAudio').setLevel(10)

        self.assertIsNotNone(self.mc.sound_system)

        if self.mc.sound_system.audio_interface is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system audio interface could not be loaded - skipping audio tests")
            self.skipTest("Sound system audio interface could not be loaded")

        self.assertIsNotNone(self.mc.sound_system.audio_interface)
        settings = self.mc.sound_system.audio_interface.get_settings()
        self.assertIsNotNone(settings)
        self.assertIn(settings['buffer_samples'], [1024, 2048])
        self.assertIn(settings['audio_channels'], [1, 2])
        self.assertEqual(settings['sample_rate'], 44100)
