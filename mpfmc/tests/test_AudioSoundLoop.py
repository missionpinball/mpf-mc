import logging

from mpfmc.tests.MpfMcTestCase import MpfMcTestCase
from unittest.mock import MagicMock, call

try:
    from mpfmc.core.audio import SoundSystem
    from mpfmc.assets.sound import SoundStealingMethod
except ImportError:
    SoundSystem = None
    SoundStealingMethod = None
    logging.warning("mpfmc.core.audio library could not be loaded. Audio "
                    "features will not be available")


class TestAudioSoundLoop(MpfMcTestCase):
    """
    """
    def get_machine_path(self):
        return 'tests/machine_files/audio'

    def get_config_file(self):
        return 'test_audio_sound_loop.yaml'

    def test_sound_loop_track(self):
        """ Tests the Sound Loop track type and its associated assets"""

        if SoundSystem is None or self.mc.sound_system is None:
            log = logging.getLogger('TestAudioSoundLoop')
            log.warning("Sound system is not enabled - skipping audio tests")
            self.skipTest("Sound system is not enabled")

        self.assertIsNotNone(self.mc.sound_system)
        interface = self.mc.sound_system.audio_interface
        self.assertIsNotNone(interface)

        # Check sound loop track
        track_loops = interface.get_track_by_name("loops")
        self.assertIsNotNone(track_loops)
        self.assertEqual(track_loops.name, "loops")
        self.assertAlmostEqual(track_loops.volume, 0.6, 1)

        # /sounds/loops
        self.assertTrue(hasattr(self.mc, 'sounds'))
        self.assertIn('kick', self.mc.sounds)
        self.assertIn('hihat', self.mc.sounds)
        self.assertIn('snare', self.mc.sounds)
        self.assertIn('clap', self.mc.sounds)

        # Sound loop sets
        self.assertTrue(hasattr(self.mc, 'sound_loop_sets'))
        self.assertIn('basic_beat', self.mc.sound_loop_sets)

        # Test sound_loop_player
        self.mc.events.post('play_basic_beat')
        self.advance_time()
        self.advance_real_time(2)
