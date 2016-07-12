import logging
from mpfmc.tests.MpfMcTestCase import MpfMcTestCase
from mock import MagicMock


class TestAudio(MpfMcTestCase):
    """
    Tests all the audio features in the media controller.  The core audio library is a
    custom extension library written in Cython that interfaces with the SDL2 and
    SDL_Mixer libraries.
    """
    def get_machine_path(self):
        return 'tests/machine_files/audio'

    def get_config_file(self):
        return 'test_audio.yaml'

    def get_sound_file_path(self):
        return 'tests/machine_files/audio/sounds'

    def test_typical_sound_system(self):
        """ Tests the sound system and audio interface with typical settings """

        if self.mc.sound_system is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system is not enabled - unable to run audio tests")
            return

        self.assertIsNotNone(self.mc.sound_system)
        interface = self.mc.sound_system.audio_interface
        self.assertIsNotNone(interface)

        # Check basic audio interface settings
        settings = interface.get_settings()
        self.assertIsNotNone(settings)
        self.assertEqual(settings['buffer_samples'], 4096)
        self.assertEqual(settings['audio_channels'], 2)
        self.assertEqual(settings['sample_rate'], 44100)

        # Check static conversion functions (gain, samples)
        self.assertEqual(interface.string_to_gain('0db'), 1.0)
        self.assertAlmostEqual(interface.string_to_gain('-3 db'), 0.707945784)
        self.assertAlmostEqual(interface.string_to_gain('-6 db'), 0.501187233)
        self.assertAlmostEqual(interface.string_to_gain('-17.5 db'), 0.133352143)
        self.assertEqual(interface.string_to_gain('3db'), 1.0)
        self.assertEqual(interface.string_to_gain('0.25'), 0.25)
        self.assertEqual(interface.string_to_gain('-3'), 0.0)

        self.assertEqual(interface.string_to_samples("234"), 234)
        self.assertEqual(interface.string_to_samples("234.73"), 234)
        self.assertEqual(interface.string_to_samples("-23"), -23)
        self.assertEqual(interface.string_to_samples("2s"), 88200)
        self.assertEqual(interface.string_to_samples("2 ms"), 88)
        self.assertEqual(interface.string_to_samples("23.5 ms"), 1036)
        self.assertEqual(interface.string_to_samples("-2 ms"), -88)

        # Check tracks
        self.assertEqual(interface.get_track_count(), 3)
        track_voice = interface.get_track_by_name("voice")
        self.assertIsNotNone(track_voice)
        self.assertEqual(track_voice.name, "voice")
        self.assertAlmostEqual(track_voice.volume, 0.6)
        self.assertEqual(track_voice.max_simultaneous_sounds, 1)

        track_sfx = interface.get_track_by_name("sfx")
        self.assertIsNotNone(track_sfx)
        self.assertEqual(track_sfx.name, "sfx")
        self.assertAlmostEqual(track_sfx.volume, 0.4)
        self.assertEqual(track_sfx.max_simultaneous_sounds, 8)

        track_music = interface.get_track_by_name("music")
        self.assertIsNotNone(track_music)
        self.assertEqual(track_music.name, "music")
        self.assertAlmostEqual(track_music.volume, 0.5)
        self.assertEqual(track_music.max_simultaneous_sounds, 1)

        self.assertTrue(self.mc, 'sounds')

        # Mock BCP send method
        self.mc.bcp_processor.send = MagicMock()

        # Allow some time for sound assets to load
        self.advance_time(2)

        # Start mode
        self.send(bcp_command='mode_start', name='mode1', priority=500)
        self.assertTrue(self.mc.modes['mode1'].active)
        self.assertEqual(self.mc.modes['mode1'].priority, 500)

        # /sounds/sfx
        self.assertIn('198361_sfx-028', self.mc.sounds)     # .wav
        self.assertIn('210871_synthping', self.mc.sounds)   # .wav
        self.assertIn('264828_text', self.mc.sounds)        # .ogg
        self.assertIn('4832__zajo__drum07', self.mc.sounds)   # .wav
        self.assertIn('84480__zgump__drum-fx-4', self.mc.sounds)   # .wav
        self.assertIn('100184__menegass__rick-drum-bd-hard', self.mc.sounds)   # .wav

        # Test bad sound file
        self.assertIn('bad_sound_file', self.mc.sounds)
        with self.assertRaises(Exception):
            self.mc.sounds['bad_sound_file'].do_load()
        self.assertFalse(self.mc.sounds['bad_sound_file'].loaded)

        # /sounds/voice
        self.assertIn('104457_moron_test', self.mc.sounds)  # .wav
        self.assertIn('113690_test', self.mc.sounds)        # .wav

        # /sounds/music
        self.assertIn('263774_music', self.mc.sounds)       # .wav

        # Sound groups
        self.assertIn('drum_group', self.mc.sounds)

        # Check if sounds are in special sounds_by_id list
        self.assertIn(self.mc.sounds['104457_moron_test'].id, self.mc.sounds_by_id)
        self.assertIn(self.mc.sounds['210871_synthping'].id, self.mc.sounds_by_id)

        # Make sure sound has ducking (since it was specified in the config files)
        self.assertTrue(self.mc.sounds['104457_moron_test'].has_ducking)

        # Test baseline internal audio event count
        self.assertEqual(interface.get_in_use_sound_event_count(), 0)


        # Test sound_player
        self.assertFalse(track_sfx.sound_is_playing(self.mc.sounds['264828_text']))
        self.mc.events.post('play_sound_text')
        self.mc.events.post('play_sound_music')
        self.advance_time(1)
        self.assertTrue(track_sfx.sound_is_playing(self.mc.sounds['264828_text']))

        # Test two sounds at the same time on the voice track (only
        # 1 sound at a time max).  Second sound should be queued and
        # play immediately after the first one ends.
        self.assertEqual(track_voice.get_sound_queue_count(), 0)
        self.mc.events.post('play_sound_test')
        self.advance_time()

        # Make sure first sound is playing on the voice track
        self.assertEqual(track_voice.get_status()[0]['sound_id'], self.mc.sounds['113690_test'].id)
        self.mc.events.post('play_sound_moron_test')
        self.advance_time()

        # Make sure first sound is still playing and the second one has been queued
        self.assertEqual(track_voice.get_status()[0]['sound_id'], self.mc.sounds['113690_test'].id)
        self.assertEqual(track_voice.get_sound_queue_count(), 1)
        self.assertTrue(track_voice.sound_is_in_queue(self.mc.sounds['104457_moron_test']))
        self.advance_time(0.1)

        # Now stop sound that is not yet playing but is queued (should be removed from queue)
        self.mc.events.post('stop_sound_moron_test')
        self.advance_time(0.25)
        self.assertFalse(track_voice.sound_is_in_queue(self.mc.sounds['104457_moron_test']))

        # Play moron test sound again (should be added to queue)
        self.mc.events.post('play_sound_moron_test')
        self.advance_time(0.1)
        self.assertTrue(track_voice.sound_is_in_queue(self.mc.sounds['104457_moron_test']))

        # Make sure text sound is still playing (looping)
        self.assertTrue(track_sfx.sound_is_playing(self.mc.sounds['264828_text']))

        # Ensure sound.events_when_looping is working properly (send event when a sound loops)
        self.mc.bcp_processor.send.assert_any_call('trigger', name='text_sound_looping')

        # Send an event to stop the text sound looping
        self.mc.events.post('stop_sound_looping_text')
        self.advance_time(2)

        # Text sound should no longer be playing
        self.assertFalse(track_sfx.sound_is_playing(self.mc.sounds['264828_text']))

        self.advance_time(2.7)
        self.mc.events.post('play_sound_synthping')
        self.advance_time(3)
        self.mc.events.post('play_sound_synthping')
        self.advance_time(6)
        self.mc.events.post('stop_sound_music')
        self.mc.events.post('play_sound_synthping_in_mode')
        self.advance_time(1)
        self.mc.events.post('play_sound_synthping')
        self.advance_time(1)

        # Test playing sound pool (many times)
        for x in range(16):
            self.mc.events.post('play_sound_drum_group')
            self.advance_time(0.1)

        self.mc.events.post('play_sound_drum_group_in_mode')
        self.advance_time(1)

        # Test stopping the mode
        self.send(bcp_command='mode_stop', name='mode1')
        self.advance_time(1)

        # Test sound events
        self.mc.bcp_processor.send.assert_any_call('trigger', name='moron_test_played')
        self.mc.bcp_processor.send.assert_any_call('trigger', name='moron_test_stopped')
        self.mc.bcp_processor.send.assert_any_call('trigger', name='synthping_played')

        # Check for internal sound event processing leaks (are there any internal sound
        # events that get generated, but never processed and cleared from the queue?)
        self.assertEqual(interface.get_in_use_sound_event_count(), 0)

        """
        # Add another track with the same name (should not be allowed)
        # Add another track with the same name, but different casing (should not be allowed)
        # Attempt to create track with max_simultaneous_sounds > 32 (the current max)
        # Attempt to create track with max_simultaneous_sounds < 1 (the current max)
        # Add up to the maximum number of tracks allowed
        # There should now be the maximum number of tracks allowed
        # Try to add another track (more than the maximum allowed)

        # TODO: Tests to write:
        # Load sounds (wav, ogg, flac, unsupported format)
        # Play a sound
        # Play two sounds on track with max_simultaneous_sounds = 1 (test sound queue,
        time expiration, priority scenarios)
        # Play a sound on each track simultaneously
        # Stop all sounds on track
        # Stop all sounds on all tracks
        # Ducking
        # Configuration file tests (audio interface, tracks, sounds, sound player, sound
        # trigger events, etc.)
        #
        """
