import logging

from mpfmc.tests.MpfMcTestCase import MpfMcTestCase
from unittest.mock import MagicMock, ANY

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
        if interface is None:
            log = logging.getLogger('TestAudioSoundLoop')
            log.warning("Sound system audio interface could not be loaded - skipping audio tests")
            self.skipTest("Sound system audio interface could not be loaded")

        self.assertIsNotNone(interface)

        # Check sound loop track
        track_loops = interface.get_track_by_name("loops")
        self.assertIsNotNone(track_loops)
        self.assertEqual(track_loops.name, "loops")
        self.assertAlmostEqual(track_loops.volume, 0.6, 1)

        # /sounds/loops
        self.assertTrue(hasattr(self.mc, 'sounds'))
        self.assertIn('kick', self.mc.sounds)
        self.assertIn('kick2', self.mc.sounds)
        self.assertIn('hihat', self.mc.sounds)
        self.assertIn('snare', self.mc.sounds)
        self.assertIn('clap', self.mc.sounds)
        self.assertIn('bass_synth', self.mc.sounds)

        self.assertEqual(1, self.mc.sounds["kick"].marker_count)
        self.assertEqual(2, self.mc.sounds["hihat"].marker_count)

        # Sound loop sets
        self.assertTrue(hasattr(self.mc, 'sound_loop_sets'))
        self.assertIn('basic_beat', self.mc.sound_loop_sets)
        self.assertIn('basic_beat2', self.mc.sound_loop_sets)

        # Mock BCP send method
        self.mc.bcp_processor.send = MagicMock()
        self.mc.bcp_processor.enabled = True

        # Test sound_loop_player
        self.advance_time()
        self.mc.events.post('play_sound_synthping')
        self.mc.events.post('play_basic_beat')
        self.advance_real_time(1)

        # Ensure sound_loop_set.events_when_played is working properly (send event when a sound_loop_set is played)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='basic_beat_played')

        self.mc.events.post('add_hi_hats')
        self.advance_time()
        self.advance_real_time(3)

        self.mc.events.post('add_snare')
        self.mc.events.post('add_claps')
        self.advance_real_time(2)

        # Ensure sound_loop_set.events_when_looping is working properly (send event when a sound_loop_set loops)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='basic_beat_looping')

        # Ensure sound marker events are working properly for underlying sounds
        self.mc.bcp_processor.send.assert_any_call('trigger', name='kick_marker_1', sound_instance=ANY, marker_id=0)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='hihat_marker_1', sound_instance=ANY, marker_id=0)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='hihat_marker_2', sound_instance=ANY, marker_id=1)

        status = track_loops.get_status()
        self.assertEqual(status[0]['status'], "playing")
        self.assertEqual(status[0]['sound_id'], self.mc.sounds["kick"].id)
        self.assertTrue(status[0]['looping'])
        self.assertEqual(len(status[0]['layers']), 3)
        self.assertEqual(status[1]['status'], "idle")
        self.advance_real_time(2)

        self.mc.events.post('play_basic_beat2')
        self.advance_real_time(4)
        status = track_loops.get_status()
        self.assertEqual(status[0]['status'], "playing")
        self.assertEqual(status[0]['sound_id'], self.mc.sounds["kick2"].id)
        self.assertTrue(status[0]['looping'])
        self.assertEqual(len(status[0]['layers']), 4)

        # Ensure sound_loop_set.events_when_stopped is working properly (send event when a sound_loop_set stops)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='basic_beat_stopped')
        self.mc.bcp_processor.send.assert_any_call('trigger', name='sound_loop_set_stopped')

        self.mc.events.post('fade_out_bass_synth')
        self.advance_real_time(4)

        self.mc.events.post('reset_current_loop')
        self.advance_real_time(0.1)
        self.mc.events.post('reset_current_loop')
        self.advance_real_time(0.1)
        self.mc.events.post('reset_current_loop')
        self.advance_real_time(0.1)
        self.mc.events.post('reset_current_loop')
        self.advance_real_time(0.2)
        self.mc.events.post('reset_current_loop')
        self.advance_real_time(0.1)

        self.mc.events.post('play_basic_beat')
        self.mc.events.post('stop_current_loop')
        self.mc.events.post('play_sound_synthping')
        self.advance_real_time(2)

        # Make sure next pending sound_loop_set is cancelled with stop action
        status = track_loops.get_status()
        self.assertEqual(status[1]['status'], "idle")
