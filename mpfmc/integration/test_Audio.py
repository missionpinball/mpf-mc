from mpfmc.tests.MpfIntegrationTestCase import MpfIntegrationTestCase

try:
    from mpfmc.core.audio import SoundSystem
except ImportError:
    SoundSystem = None


class TestAudio(MpfIntegrationTestCase):

    def get_machine_path(self):
        return 'integration/machine_files/audio'

    def get_config_file(self):
        return 'config.yaml'

    def test_sound_custom_code(self):

        if SoundSystem is None or self.mc.sound_system is None:
            self.skipTest("Sound system is not enabled")

        self.assertIsNotNone(self.mc.sound_system)
        interface = self.mc.sound_system.audio_interface
        if interface is None:
            self.skipTest("Sound system audio interface could not be loaded")

        self.assertIsNotNone(interface)

        # Check sfx track
        track_sfx = interface.get_track_by_name("sfx")
        self.assertIsNotNone(track_sfx)
        self.assertEqual(track_sfx.name, "sfx")
        self.assertAlmostEqual(track_sfx.volume, 0.6, 1)

        # /sounds/sfx
        self.assertTrue(hasattr(self.mc, 'sounds'))
        self.assertIn('264828_text', self.mc.sounds)

        # Attempt to play sound by calling sound_player directly from custom code
        settings = {
            '264828_text': {
                'action': 'play',
                'loops': -1,
                'key': 'music',
                'block': False,
            }
        }
        self.machine.sound_player.play(settings, 'asset_manager', None)
        self.advance_time_and_run(0.2)

        status = track_sfx.get_status()
        self.assertEqual(status[0]['status'], "playing")
        self.assertEqual(status[0]['sound_id'], self.mc.sounds["264828_text"].id)
        self.assertEqual(len(status), 1)

        settings = {
            '264828_text': {
                'action': 'stop',
                'block': False,
            }
        }
        self.machine.sound_player.play(settings, 'asset_manager', None)
        self.advance_time_and_run(0.1)

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
        self.assertEqual(status[0]['stop_loop_samples_remaining'], "DO NOT STOP LOOP")
        self.assertEqual(len(status), 1)

        self.post_event('stop_current_loop')
        self.advance_time_and_run(3)

    def test_sound_player_and_show(self):

        if SoundSystem is None or self.mc.sound_system is None:
            self.skipTest("Sound system is not enabled")

        self.assertIsNotNone(self.mc.sound_system)
        interface = self.mc.sound_system.audio_interface
        if interface is None:
            self.skipTest("Sound system audio interface could not be loaded")

        self.assertIsNotNone(interface)

        # Make sure sound assets are present
        self.assertTrue(hasattr(self.mc, 'sounds'))
        self.assertIn('264828_text', self.mc.sounds)

        self.mock_event("use_sound_setting")
        self.mock_event("text_sound_played")
        self.mock_event("text_sound_played_from_show")
        self.mock_event("text_sound_played_from_sound_player")
        self.mock_event("text_sound_stopped")
        self.mock_event("text_sound_stopped_from_show")
        self.mock_event("text_sound_stopped_from_sound_player")

        # Play sound using sound player
        self.post_event('play_sound_1')
        self.advance_time_and_run(0.1)
        self.assertEventNotCalled("use_sound_setting")
        self.assertEventNotCalled("text_sound_played")
        self.assertEventCalled("text_sound_played_from_sound_player")

        self.post_event("stop_sound")
        self.advance_time_and_run(0.1)
        self.assertEventNotCalled("use_sound_setting")
        self.assertEventNotCalled("text_sound_stopped")
        self.assertEventCalled("text_sound_stopped_from_sound_player")
        self.reset_mock_events()

        self.post_event('play_sound_2')
        self.advance_time_and_run(0.1)
        self.assertEventNotCalled("use_sound_setting")
        self.assertEventNotCalled("text_sound_played_from_sound_player")
        self.assertEventCalled("text_sound_played")

        self.post_event("stop_sound")
        self.advance_time_and_run(0.1)
        self.assertEventNotCalled("use_sound_setting")
        self.assertEventCalled("text_sound_stopped")
        self.assertEventNotCalled("text_sound_stopped_from_sound_player")
        self.reset_mock_events()

        self.post_event('play_sound_3')
        self.advance_time_and_run(0.1)
        self.assertEventNotCalled("use_sound_setting")
        self.assertEventNotCalled("text_sound_played_from_sound_player")
        self.assertEventNotCalled("text_sound_played")

        self.post_event("stop_sound")
        self.advance_time_and_run(0.1)
        self.assertEventNotCalled("use_sound_setting")
        self.assertEventCalled("text_sound_stopped")
        self.assertEventNotCalled("text_sound_stopped_from_sound_player")
        self.reset_mock_events()

        # Play first show
        self.post_event('play_sound_test_1_show')
        self.advance_time_and_run(0.1)
        self.assertEventNotCalled("use_sound_setting")
        self.assertEventNotCalled("text_sound_played")
        self.assertEventCalled("text_sound_played_from_show")

        self.post_event("stop_sound")
        self.advance_time_and_run(0.1)
        self.assertEventNotCalled("use_sound_setting")
        self.assertEventNotCalled("text_sound_stopped")
        self.assertEventCalled("text_sound_stopped_from_show")
        self.reset_mock_events()

        # Play second show
        self.post_event('play_sound_test_2_show')
        self.advance_time_and_run(0.1)
        self.assertEventNotCalled("use_sound_setting")
        self.assertEventNotCalled("text_sound_played_from_show")
        self.assertEventCalled("text_sound_played")

        self.post_event("stop_sound")
        self.advance_time_and_run(0.1)
        self.assertEventNotCalled("use_sound_setting")
        self.assertEventCalled("text_sound_stopped")
        self.assertEventNotCalled("text_sound_stopped_from_show")
        self.reset_mock_events()

        # Play third show
        self.post_event('play_sound_test_3_show')
        self.advance_time_and_run(0.1)
        self.assertEventNotCalled("use_sound_setting")
        self.assertEventNotCalled("text_sound_played_from_show")
        self.assertEventNotCalled("text_sound_played")

        self.post_event("stop_sound")
        self.advance_time_and_run(0.1)
        self.assertEventNotCalled("use_sound_setting")
        self.assertEventCalled("text_sound_stopped")
        self.assertEventNotCalled("text_sound_stopped_from_show")
