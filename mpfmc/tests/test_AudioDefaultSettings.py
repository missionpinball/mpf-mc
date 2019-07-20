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
            self.skipTest("Sound system is not enabled")

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

        # /sounds/sfx
        self.assertIn('198361_sfx-028', self.mc.sounds)     # .wav
        self.assertIn('210871_synthping', self.mc.sounds)   # .wav
        self.assertIn('264828_text', self.mc.sounds)        # .ogg
        self.assertIn('4832__zajo__drum07', self.mc.sounds)   # .wav
        self.assertIn('84480__zgump__drum-fx-4', self.mc.sounds)   # .wav
        self.assertIn('100184__menegass__rick-drum-bd-hard', self.mc.sounds)   # .wav

        # /sounds/voice
        self.assertIn('104457_moron_test', self.mc.sounds)  # .wav
        self.assertIn('113690_test', self.mc.sounds)        # .wav

        # Check for default ducking assigned only to sounds in the sfx folder
        self.assertTrue(self.mc.sounds['198361_sfx-028'].has_ducking)
        self.assertEqual(0, self.mc.sounds['198361_sfx-028'].ducking.delay)
        self.assertEqual(0.3, self.mc.sounds['198361_sfx-028'].ducking.attack)
        self.assertEqual(0.45, self.mc.sounds['198361_sfx-028'].ducking.attenuation)
        self.assertEqual(0.5, self.mc.sounds['198361_sfx-028'].ducking.release_point)
        self.assertEqual(1.0, self.mc.sounds['198361_sfx-028'].ducking.release)
        self.assertTrue(self.mc.sounds['210871_synthping'].has_ducking)
        self.assertTrue(self.mc.sounds['264828_text'].has_ducking)
        self.assertTrue(self.mc.sounds['4832__zajo__drum07'].has_ducking)
        self.assertTrue(self.mc.sounds['84480__zgump__drum-fx-4'].has_ducking)
        self.assertTrue(self.mc.sounds['100184__menegass__rick-drum-bd-hard'].has_ducking)

        # These sounds should not have ducking
        self.assertFalse(self.mc.sounds['104457_moron_test'].has_ducking)
        self.assertFalse(self.mc.sounds['113690_test'].has_ducking)
