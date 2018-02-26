from mpfmc.tests.MpfIntegrationTestCase import MpfIntegrationTestCase

try:
    from mpfmc.core.audio import SoundSystem
except ImportError:
    SoundSystem = None


class TestAudio(MpfIntegrationTestCase):

    def getMachinePath(self):
        return 'integration/machine_files/audio'

    def getConfigFile(self):
        return 'config.yaml'

    def test_sound_loop_player(self):

        if SoundSystem is None or self.mc.sound_system is None:
            self.skipTest("Sound system is not enabled")

        self.assertIsNotNone(self.mc.sound_system)
        interface = self.mc.sound_system.audio_interface
        if interface is None:
            self.skipTest("Sound system audio interface could not be loaded")

        self.assertIsNotNone(interface)

        # start mode1, its slide with video should come up
        self.post_event("start_mode1")
        self.advance_time_and_run()

        self.assertEqual(self.mc.targets['default'].current_slide.name, 'mode1_slide1')

        # Check sound loop track
        track_loops = interface.get_track_by_name("loops")
        self.assertIsNotNone(track_loops)
        self.assertEqual(track_loops.name, "loops")
        self.assertAlmostEqual(track_loops.volume, 0.6, 1)

        # /sounds/loops
        self.assertTrue(hasattr(self.mc, 'sounds'))
        self.assertIn('kick', self.mc.sounds)

        # Sound loop sets
        self.assertTrue(hasattr(self.mc, 'sound_loop_sets'))
        self.assertIn('basic_beat', self.mc.sound_loop_sets)

        # Test sound_loop_player
        self.advance_time_and_run()
        self.post_event('play_basic_beat')
        self.advance_time_and_run(6)

        status = track_loops.get_status()
        self.assertEqual(status[0]['status'], "playing")
        self.assertEqual(status[0]['sound_id'], self.mc.sounds["kick"].id)
        self.assertTrue(status[0]['looping'])
        self.assertEqual(status[1]['status'], "idle")

        self.post_event('stop_current_loop')
        self.advance_time_and_run(3)
