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

    """Test audio sound loops."""

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
        self.assertIn('hihat', self.mc.sounds)
        self.assertIn('kick', self.mc.sounds)
        self.assertIn('kick2', self.mc.sounds)

        # Sound loop sets
        self.assertTrue(hasattr(self.mc, 'sound_loop_sets'))
        self.assertIn('hi_hat', self.mc.sound_loop_sets)
        self.assertIn('basic_beat', self.mc.sound_loop_sets)
        self.assertIn('basic_beat2', self.mc.sound_loop_sets)

        # Mock BCP send method
        self.mc.bcp_processor.send = MagicMock()
        self.mc.bcp_processor.enabled = True

        # Test sound_loop_player
        self.advance_time()
        status = track_loops.get_status()
        self.assertEqual(0, len(status))

        self.mc.events.post('play_hi_hat')
        self.advance_real_time(1)
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(325660, status[0]['length'])
        self.assertEqual(self.mc.sounds['hihat'].id, status[0]['sound_id'])
        self.assertEqual(130.0, status[0]['tempo'])

        # Ensure sound_loop_set.events_when_played is working properly (send event when a sound_loop_set is played)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='hi_hat_played')

        self.advance_real_time(2)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='hi_hat_looping')
        self.mc.bcp_processor.send.reset_mock()

        self.mc.events.post('play_basic_beat')
        self.advance_real_time(0.1)
        status = track_loops.get_status()
        self.assertEqual(2, len(status))
        self.assertEqual('delayed', status[0]['status'])
        self.assertEqual(325660, status[0]['length'])
        self.assertEqual(self.mc.sounds['kick'].id, status[0]['sound_id'])
        self.assertEqual('playing', status[1]['status'])
        self.assertEqual(325660, status[1]['length'])
        self.assertEqual(self.mc.sounds['hihat'].id, status[1]['sound_id'])
        self.assertEqual(status[0]['start_delay_samples_remaining'], status[1]['stop_loop_samples_remaining'])

        self.advance_real_time(2)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='hi_hat_stopped')
        self.mc.bcp_processor.send.assert_any_call('trigger', name='basic_beat_played')
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(325660, status[0]['length'])
        self.assertEqual(self.mc.sounds['kick'].id, status[0]['sound_id'])

        self.advance_real_time(2)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='basic_beat_looping')
        self.mc.bcp_processor.send.reset_mock()
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(325660, status[0]['length'])
        self.assertEqual(self.mc.sounds['kick'].id, status[0]['sound_id'])

        self.mc.events.post('play_hi_hat')
        self.advance_real_time(0.1)
        status = track_loops.get_status()
        self.assertEqual(2, len(status))
        self.assertEqual('delayed', status[0]['status'])
        self.assertEqual(325660, status[0]['length'])
        self.assertEqual(self.mc.sounds['hihat'].id, status[0]['sound_id'])
        self.assertEqual('playing', status[1]['status'])
        self.assertEqual(325660, status[1]['length'])
        self.assertEqual(self.mc.sounds['kick'].id, status[1]['sound_id'])
        self.assertEqual(status[0]['start_delay_samples_remaining'], status[1]['stop_loop_samples_remaining'])

        self.advance_real_time(2)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='basic_beat_stopped')
        self.mc.bcp_processor.send.assert_any_call('trigger', name='hi_hat_played')
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(325660, status[0]['length'])
        self.assertEqual(self.mc.sounds['hihat'].id, status[0]['sound_id'])

        self.advance_real_time(2)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='hi_hat_looping')
        self.mc.bcp_processor.send.reset_mock()
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(325660, status[0]['length'])
        self.assertEqual(self.mc.sounds['hihat'].id, status[0]['sound_id'])

        self.mc.events.post('play_basic_beat2')
        self.advance_real_time(0.1)
        status = track_loops.get_status()
        self.assertEqual(2, len(status))
        self.assertEqual('delayed', status[0]['status'])
        self.assertEqual(325660, status[0]['length'])
        self.assertEqual(self.mc.sounds['kick2'].id, status[0]['sound_id'])
        self.assertEqual('playing', status[1]['status'])
        self.assertEqual(325660, status[1]['length'])
        self.assertEqual(self.mc.sounds['hihat'].id, status[1]['sound_id'])
        self.assertEqual(status[0]['start_delay_samples_remaining'], status[1]['stop_loop_samples_remaining'])

        self.advance_real_time(2)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='hi_hat_stopped')
        self.mc.bcp_processor.send.assert_any_call('trigger', name='basic_beat2_played')
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(325660, status[0]['length'])
        self.assertEqual(self.mc.sounds['kick2'].id, status[0]['sound_id'])

        self.advance_real_time(2)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='basic_beat2_looping')
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(325660, status[0]['length'])
        self.assertEqual(self.mc.sounds['kick2'].id, status[0]['sound_id'])

    def test_sound_loop_track_layers(self):
        """ Tests the Sound Loop track layers"""

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
        self.assertIn('basic_beat_layers', self.mc.sound_loop_sets)
        self.assertIn('basic_beat_layers2', self.mc.sound_loop_sets)

        # Mock BCP send method
        self.mc.bcp_processor.send = MagicMock()
        self.mc.bcp_processor.enabled = True

        # Test sound_loop_player
        self.advance_time()
        self.mc.events.post('play_sound_synthping')
        self.mc.events.post('play_basic_beat_layers')
        self.advance_real_time(0.1)
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(325660, status[0]['length'])
        self.assertEqual(self.mc.sounds['kick'].id, status[0]['sound_id'])
        self.assertEqual(130.0, status[0]['tempo'])
        self.assertEqual(3, len(status[0]['layers']))
        self.assertEqual('stopped', status[0]['layers'][0]['status'])
        self.assertEqual('stopped', status[0]['layers'][1]['status'])
        self.assertEqual('stopped', status[0]['layers'][2]['status'])
        self.assertEqual(self.mc.sounds['hihat'].id, status[0]['layers'][0]['sound_id'])
        self.assertEqual(self.mc.sounds['snare'].id, status[0]['layers'][1]['sound_id'])
        self.assertEqual(self.mc.sounds['clap'].id, status[0]['layers'][2]['sound_id'])

        self.advance_real_time(0.9)

        # Ensure sound_loop_set.events_when_played is working properly (send event when a sound_loop_set is played)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='basic_beat_layers_played')

        self.mc.events.post('add_hi_hats')
        self.advance_time()
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(self.mc.sounds['kick'].id, status[0]['sound_id'])
        self.assertEqual(3, len(status[0]['layers']))
        self.assertEqual('queued', status[0]['layers'][0]['status'])
        self.assertEqual('stopped', status[0]['layers'][1]['status'])
        self.assertEqual('stopped', status[0]['layers'][2]['status'])
        self.assertEqual(self.mc.sounds['hihat'].id, status[0]['layers'][0]['sound_id'])
        self.assertEqual(self.mc.sounds['snare'].id, status[0]['layers'][1]['sound_id'])
        self.assertEqual(self.mc.sounds['clap'].id, status[0]['layers'][2]['sound_id'])

        self.advance_real_time(3)
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(self.mc.sounds['kick'].id, status[0]['sound_id'])
        self.assertEqual(3, len(status[0]['layers']))
        self.assertEqual('playing', status[0]['layers'][0]['status'])
        self.assertEqual('stopped', status[0]['layers'][1]['status'])
        self.assertEqual('stopped', status[0]['layers'][2]['status'])
        self.assertEqual(self.mc.sounds['hihat'].id, status[0]['layers'][0]['sound_id'])
        self.assertEqual(self.mc.sounds['snare'].id, status[0]['layers'][1]['sound_id'])
        self.assertEqual(self.mc.sounds['clap'].id, status[0]['layers'][2]['sound_id'])

        self.mc.events.post('add_snare')
        self.mc.events.post('add_claps')
        self.advance_real_time(2)
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(self.mc.sounds['kick'].id, status[0]['sound_id'])
        self.assertEqual(3, len(status[0]['layers']))
        self.assertEqual('playing', status[0]['layers'][0]['status'])
        self.assertEqual('playing', status[0]['layers'][1]['status'])
        self.assertEqual('playing', status[0]['layers'][2]['status'])
        self.assertEqual(self.mc.sounds['hihat'].id, status[0]['layers'][0]['sound_id'])
        self.assertEqual(self.mc.sounds['snare'].id, status[0]['layers'][1]['sound_id'])
        self.assertEqual(self.mc.sounds['clap'].id, status[0]['layers'][2]['sound_id'])

        # Ensure sound_loop_set.events_when_looping is working properly (send event when a sound_loop_set loops)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='basic_beat_layers_looping')

        # Ensure sound marker events are working properly for underlying sounds
        self.mc.bcp_processor.send.assert_any_call('trigger', name='kick_marker_1', sound_instance=ANY, marker_id=0)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='hihat_marker_1', sound_instance=ANY, marker_id=0)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='hihat_marker_2', sound_instance=ANY, marker_id=1)

        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(self.mc.sounds["kick"].id, status[0]['sound_id'])
        self.assertEqual(3, len(status[0]['layers']))
        self.assertEqual('playing', status[0]['layers'][0]['status'])
        self.assertEqual('playing', status[0]['layers'][1]['status'])
        self.assertEqual('playing', status[0]['layers'][2]['status'])
        self.assertEqual(self.mc.sounds['hihat'].id, status[0]['layers'][0]['sound_id'])
        self.assertEqual(self.mc.sounds['snare'].id, status[0]['layers'][1]['sound_id'])
        self.assertEqual(self.mc.sounds['clap'].id, status[0]['layers'][2]['sound_id'])
        self.advance_real_time(2)

        self.mc.events.post('play_basic_beat_layers2')
        self.advance_time()
        status = track_loops.get_status()
        self.assertEqual(2, len(status))
        self.assertEqual('delayed', status[0]['status'])
        self.assertEqual(self.mc.sounds["kick2"].id, status[0]['sound_id'])
        self.assertEqual('playing', status[1]['status'])
        self.assertEqual(self.mc.sounds["kick"].id, status[1]['sound_id'])
        self.assertEqual(status[0]['start_delay_samples_remaining'], status[1]['stop_loop_samples_remaining'])

        self.advance_real_time(4)
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(self.mc.sounds["kick2"].id, status[0]['sound_id'])
        self.assertEqual(4, len(status[0]['layers']))
        self.assertEqual('playing', status[0]['layers'][0]['status'])
        self.assertEqual('playing', status[0]['layers'][1]['status'])
        self.assertEqual('stopped', status[0]['layers'][2]['status'])
        self.assertEqual('playing', status[0]['layers'][3]['status'])
        self.assertEqual(self.mc.sounds['hihat'].id, status[0]['layers'][0]['sound_id'])
        self.assertEqual(self.mc.sounds['snare'].id, status[0]['layers'][1]['sound_id'])
        self.assertEqual(self.mc.sounds['clap'].id, status[0]['layers'][2]['sound_id'])
        self.assertEqual(self.mc.sounds['bass_synth'].id, status[0]['layers'][3]['sound_id'])

        # Ensure sound_loop_set.events_when_stopped is working properly (send event when a sound_loop_set stops)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='basic_beat_layers_stopped')
        self.mc.bcp_processor.send.assert_any_call('trigger', name='sound_loop_set_stopped')

        self.mc.events.post('fade_out_bass_synth')
        self.advance_time()
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(self.mc.sounds["kick2"].id, status[0]['sound_id'])
        self.assertEqual(4, len(status[0]['layers']))
        self.assertEqual('playing', status[0]['layers'][0]['status'])
        self.assertEqual('playing', status[0]['layers'][1]['status'])
        self.assertEqual('stopped', status[0]['layers'][2]['status'])
        self.assertEqual('fading out', status[0]['layers'][3]['status'])
        self.assertEqual(self.mc.sounds['hihat'].id, status[0]['layers'][0]['sound_id'])
        self.assertEqual(self.mc.sounds['snare'].id, status[0]['layers'][1]['sound_id'])
        self.assertEqual(self.mc.sounds['clap'].id, status[0]['layers'][2]['sound_id'])
        self.assertEqual(self.mc.sounds['bass_synth'].id, status[0]['layers'][3]['sound_id'])
        self.assertGreater(status[0]['layers'][3]['fade_out_steps'], 0)
        self.assertGreater(status[0]['layers'][3]['fade_steps_remaining'], 0)

        self.advance_real_time(4)
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(self.mc.sounds["kick2"].id, status[0]['sound_id'])
        self.assertEqual(4, len(status[0]['layers']))
        self.assertEqual('playing', status[0]['layers'][0]['status'])
        self.assertEqual('playing', status[0]['layers'][1]['status'])
        self.assertEqual('stopped', status[0]['layers'][2]['status'])
        self.assertEqual('stopped', status[0]['layers'][3]['status'])
        self.assertEqual(self.mc.sounds['hihat'].id, status[0]['layers'][0]['sound_id'])
        self.assertEqual(self.mc.sounds['snare'].id, status[0]['layers'][1]['sound_id'])
        self.assertEqual(self.mc.sounds['clap'].id, status[0]['layers'][2]['sound_id'])
        self.assertEqual(self.mc.sounds['bass_synth'].id, status[0]['layers'][3]['sound_id'])
        self.assertGreater(status[0]['layers'][3]['fade_out_steps'], 0)
        self.assertEqual(0, status[0]['layers'][3]['fade_steps_remaining'])

        self.mc.events.post('reset_current_loop')
        self.advance_real_time(0.1)
        self.mc.events.post('reset_current_loop')
        self.advance_real_time(0.1)
        self.mc.events.post('reset_current_loop')
        self.advance_real_time(0.1)
        self.mc.events.post('reset_current_loop')
        self.advance_real_time(0.2)

        self.mc.events.post('reset_current_loop')
        self.advance_time()
        status = track_loops.get_status()
        self.assertEqual(status[0]["sample_pos"], 0)
        self.advance_real_time(0.1)

        self.mc.events.post('jump_to_middle_of_loop')
        self.advance_time()
        status = track_loops.get_status()
        self.assertAlmostEqual(status[0]['sample_pos'], status[0]["length"]//2, delta=16)
        self.advance_real_time(2)

        self.mc.events.post('play_basic_beat_layers')
        self.mc.events.post('stop_current_loop')
        self.mc.events.post('play_sound_synthping')
        self.advance_real_time(2)

        # Make sure next pending sound_loop_set is cancelled with stop action
        status = track_loops.get_status()
        self.assertEqual(0, len(status))

    def test_sound_loop_fades(self):
        """ Tests Sound Loop fading"""
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
        self.assertIn('hihat', self.mc.sounds)
        self.assertIn('kick', self.mc.sounds)
        self.assertIn('kick2', self.mc.sounds)

        # Sound loop sets
        self.assertTrue(hasattr(self.mc, 'sound_loop_sets'))
        self.assertIn('hi_hat', self.mc.sound_loop_sets)
        self.assertIn('basic_beat', self.mc.sound_loop_sets)
        self.assertIn('basic_beat2', self.mc.sound_loop_sets)

        # Play hi-hat loop and check status
        track_loops.play_sound_loop_set(self.mc.sound_loop_sets['hi_hat'])
        self.advance_real_time(0.1)
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(status[0]['sound_id'], self.mc.sounds['hihat'].id)

        # Now play kick loop and recheck status (both loops should be cross-fading and in sync)
        track_loops.play_sound_loop_set(self.mc.sound_loop_sets['basic_beat'], None,
                                        {'fade_in': 1.0, 'timing': 'now', 'synchronize': True})
        self.advance_real_time(0.1)

        status = track_loops.get_status()
        self.assertEqual('fading out', status[1]['status'])
        self.assertEqual('fading in', status[0]['status'])
        self.assertGreater(status[1]['fade_out_steps'], 0)
        self.assertGreater(status[0]['fade_in_steps'], 1)
        self.assertEqual(status[1]['sample_pos'], status[0]['sample_pos'])
        self.assertEqual(status[1]['sound_id'], self.mc.sounds['hihat'].id)
        self.assertEqual(status[0]['sound_id'], self.mc.sounds['kick'].id)

        # Recheck status (hi-hat loop should be finished and kick loop should be playing)
        self.advance_real_time(1.1)
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(status[0]['sound_id'], self.mc.sounds['kick'].id)

        # Now play hi hat loop and recheck status (both loops should be cross-fading and in sync)
        track_loops.play_sound_loop_set(self.mc.sound_loop_sets['hi_hat'], None,
                                        {'fade_in': 2.0, 'timing': 'now', 'synchronize': True})
        self.advance_real_time(0.1)

        status = track_loops.get_status()
        self.assertEqual(2, len(status))
        self.assertEqual('fading out', status[1]['status'])
        self.assertEqual('fading in', status[0]['status'])
        self.assertGreater(status[1]['fade_out_steps'], 0)
        self.assertGreater(status[0]['fade_in_steps'], 0)
        self.assertEqual(status[1]['sample_pos'], status[0]['sample_pos'])
        self.assertEqual(status[1]['sound_id'], self.mc.sounds['kick'].id)
        self.assertEqual(status[0]['sound_id'], self.mc.sounds['hihat'].id)

        self.advance_real_time(0.3)

        # Now play kick 2 and recheck status (new loop should be fading in and other two loops fading out)
        track_loops.play_sound_loop_set(self.mc.sound_loop_sets['basic_beat2'], None,
                                        {'fade_in': 0.8, 'timing': 'now', 'synchronize': False})
        self.advance_real_time(0.1)

        status = track_loops.get_status()
        self.assertEqual(3, len(status))
        self.assertEqual('fading in', status[0]['status'])
        self.assertEqual('fading out', status[1]['status'])
        self.assertEqual('fading out', status[2]['status'])
        self.assertGreater(status[0]['fade_in_steps'], 0)
        self.assertGreater(status[1]['fade_out_steps'], 0)
        self.assertGreater(status[1]['fade_out_steps'], 0)
        # don't know why this is off by one on Linux
        self.assertIn(status[0]['fade_steps_remaining'],
                      [status[1]['fade_steps_remaining'], status[1]['fade_steps_remaining'] + 1])
        self.assertIn(status[0]['fade_steps_remaining'],
                      [status[2]['fade_steps_remaining'], status[2]['fade_steps_remaining'] + 1])
        self.assertEqual(status[1]['sample_pos'], status[2]['sample_pos'])
        self.assertEqual(status[0]['sound_id'], self.mc.sounds['kick2'].id)
        self.assertEqual(status[1]['sound_id'], self.mc.sounds['hihat'].id)
        self.assertEqual(status[2]['sound_id'], self.mc.sounds['kick'].id)

    def test_sound_loop_timing_settings(self):
        """ Tests Sound Loop fading"""
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
        self.assertIn('hihat', self.mc.sounds)
        self.assertIn('kick', self.mc.sounds)
        self.assertIn('kick2', self.mc.sounds)

        # Sound loop sets
        self.assertTrue(hasattr(self.mc, 'sound_loop_sets'))
        self.assertIn('hi_hat', self.mc.sound_loop_sets)
        self.assertIn('basic_beat', self.mc.sound_loop_sets)
        self.assertIn('basic_beat2', self.mc.sound_loop_sets)

        # Play hi-hat loop and check status
        track_loops.play_sound_loop_set(self.mc.sound_loop_sets['hi_hat'])
        self.advance_real_time(0.1)
        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(status[0]['sound_id'], self.mc.sounds['hihat'].id)
        self.advance_real_time(0.5)

        # Now play kick loop and recheck status (loops should perform a quick cross-fade and switch)
        track_loops.play_sound_loop_set(self.mc.sound_loop_sets['basic_beat'], None, {'timing': 'now'})
        self.advance_real_time(0.2)

        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(status[0]['sound_id'], self.mc.sounds['kick'].id)
        self.advance_real_time(0.3)

        # Now play second kick loop and recheck status (loops should perform a quick cross-fade and switch)
        track_loops.play_sound_loop_set(self.mc.sound_loop_sets['basic_beat2'], None, {'timing': 'now'})
        self.advance_real_time(0.2)

        status = track_loops.get_status()
        self.assertEqual(1, len(status))
        self.assertEqual('playing', status[0]['status'])
        self.assertEqual(status[0]['sound_id'], self.mc.sounds['kick2'].id)
        self.advance_real_time(0.3)
