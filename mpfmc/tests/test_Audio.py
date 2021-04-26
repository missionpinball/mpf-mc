import logging

from mpfmc.tests.MpfMcTestCase import MpfMcTestCase
from unittest.mock import MagicMock, call, ANY

try:
    from mpfmc.core.audio import SoundSystem
    from mpfmc.assets.sound import SoundInstance, SoundStealingMethod, SoundPool, ModeEndAction
except ImportError:
    SoundSystem = None
    SoundInstance = None
    SoundStealingMethod = None
    ModeEndAction = None
    SoundPool = None
    logging.warning("mpfmc.core.audio library could not be loaded. Audio "
                    "features will not be available")


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

    def test_typical_sound_system(self):
        """ Tests the sound system and audio interface with typical settings """

        if SoundSystem is None or self.mc.sound_system is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system is not enabled - skipping audio tests")
            self.skipTest("Sound system is not enabled")

        self.assertIsNotNone(self.mc.sound_system)
        interface = self.mc.sound_system.audio_interface
        if interface is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system audio interface could not be loaded - skipping audio tests")
            self.skipTest("Sound system audio interface could not be loaded")

        self.assertIsNotNone(interface)

        # Check basic audio interface settings
        settings = interface.get_settings()
        self.assertIsNotNone(settings)

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

        self.assertEqual(interface.convert_seconds_to_buffer_length(2.25), 396900)
        self.assertEqual(interface.convert_buffer_length_to_seconds(396900), 2.25)

        # Check tracks
        self.assertEqual(interface.get_track_count(), 3)
        track_voice = interface.get_track_by_name("voice")
        self.assertIsNotNone(track_voice)
        self.assertEqual(track_voice.name, "voice")
        self.assertAlmostEqual(track_voice.volume, 0.6, 1)
        self.assertEqual(track_voice.max_simultaneous_sounds, 1)

        track_sfx = interface.get_track_by_name("sfx")
        self.assertIsNotNone(track_sfx)
        self.assertEqual(track_sfx.name, "sfx")
        self.assertAlmostEqual(track_sfx.volume, 0.4, 1)
        self.assertEqual(track_sfx.max_simultaneous_sounds, 8)

        track_music = interface.get_track_by_name("music")
        self.assertIsNotNone(track_music)
        self.assertEqual(track_music.name, "music")
        self.assertAlmostEqual(track_music.volume, 0.5, 1)
        self.assertEqual(track_music.max_simultaneous_sounds, 1)

        self.assertTrue(hasattr(self.mc, 'sounds'))

        # Mock BCP send method
        self.mc.bcp_processor.send = MagicMock()
        self.mc.bcp_processor.enabled = True

        # Allow some time for sound assets to load
        self.advance_real_time(2)

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

        # /sounds/voice
        self.assertIn('104457_moron_test', self.mc.sounds)  # .wav
        self.assertEqual(self.mc.sounds['104457_moron_test'].volume, 0.6)
        self.assertIn('113690_test', self.mc.sounds)        # .wav

        # /sounds/music
        self.assertIn('263774_music', self.mc.sounds)       # .wav

        # Sound groups
        self.assertIn('drum_group', self.mc.sounds)
        self.assertTrue(isinstance(self.mc.sounds['drum_group'], SoundPool))

        # Make sure sound has ducking (since it was specified in the config files)
        self.assertTrue(self.mc.sounds['104457_moron_test'].has_ducking)
        self.assertEqual(2.0, self.mc.sounds['104457_moron_test'].about_to_finish_time)
        self.assertListEqual(['moron_test_about_to_finish'],
                             self.mc.sounds['104457_moron_test'].events_when_about_to_finish)

        # Test sound_player
        self.assertFalse(track_sfx.sound_is_playing(self.mc.sounds['264828_text']))
        self.mc.events.post('play_sound_text')
        self.mc.events.post('play_sound_music')
        self.advance_real_time(1)
        self.assertTrue(track_sfx.sound_is_playing(self.mc.sounds['264828_text']))

        # Test two sounds at the same time on the voice track (only
        # 1 sound at a time max).  Second sound should be queued and
        # play immediately after the first one ends.
        self.assertEqual(track_voice.get_sound_queue_count(), 0)
        self.mc.events.post('play_sound_test')
        self.advance_real_time()

        # Make sure first sound is playing on the voice track
        self.assertEqual(track_voice.get_status()[0]['sound_id'], self.mc.sounds['113690_test'].id)
        self.mc.events.post('play_sound_moron_test')
        self.advance_real_time()

        # Make sure first sound is still playing and the second one has been queued
        self.assertEqual(track_voice.get_status()[0]['sound_id'], self.mc.sounds['113690_test'].id)
        self.assertEqual(track_voice.get_sound_queue_count(), 1)
        self.assertTrue(track_voice.sound_is_in_queue(self.mc.sounds['104457_moron_test']))
        self.advance_real_time(0.1)

        # Now stop sound that is not yet playing but is queued (should be removed from queue)
        self.mc.events.post('stop_sound_moron_test')
        self.advance_real_time(0.25)
        self.assertFalse(track_voice.sound_is_in_queue(self.mc.sounds['104457_moron_test']))

        # Play moron test sound again (should be added to queue)
        self.mc.events.post('play_sound_moron_test')
        self.advance_real_time(0.1)
        self.assertTrue(track_voice.sound_is_in_queue(self.mc.sounds['104457_moron_test']))

        # Make sure text sound is still playing (looping)
        self.assertTrue(track_sfx.sound_is_playing(self.mc.sounds['264828_text']))

        # Ensure sound.events_when_looping is working properly (send event when a sound loops)
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='text_sound_looping')

        # Send an event to stop the text sound looping
        self.mc.events.post('stop_sound_looping_text')
        self.advance_real_time(2)

        # Text sound should no longer be playing
        self.assertFalse(track_sfx.sound_is_playing(self.mc.sounds['264828_text']))

        self.advance_real_time(2.7)
        self.mc.events.post('play_sound_synthping')
        self.advance_real_time(3)
        self.assertEqual(track_voice.get_status()[0]['sound_id'], self.mc.sounds['104457_moron_test'].id)
        self.assertEqual(track_voice.get_status()[0]['volume'], 76)
        self.mc.events.post('play_sound_synthping')
        self.advance_real_time(6)
        self.mc.events.post('stop_sound_music')
        self.mc.events.post('play_sound_synthping_in_mode')
        self.advance_real_time(1)
        self.mc.events.post('play_sound_synthping')
        self.advance_real_time(1)

        # Test playing sound pool (many times)
        for x in range(16):
            self.mc.events.post('play_sound_drum_group')
            self.advance_real_time(0.1)

        self.mc.events.post('play_sound_drum_group_in_mode')
        self.advance_real_time(1)

        # Test stopping the mode
        self.send(bcp_command='mode_stop', name='mode1')
        self.advance_real_time(1)

        # Test sound events
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='moron_test_played')
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='moron_test_about_to_finish')
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='moron_test_stopped')
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='synthping_played')
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, marker_id=0, name='moron_marker')
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, marker_id=1, name='moron_next_marker')
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, marker_id=1, name='last_marker')
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, marker_id=2,
                                                   name='moron_about_to_finish_marker')

    def test_sound_instance_parameters(self):
        """Test the creation of sound instances and their parameters"""

        if SoundSystem is None or self.mc.sound_system is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system is not enabled - skipping audio tests")
            self.skipTest("Sound system is not enabled")

        self.assertIsNotNone(self.mc.sound_system)
        interface = self.mc.sound_system.audio_interface
        if interface is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system audio interface could not be loaded - skipping audio tests")
            self.skipTest("Sound system audio interface could not be loaded")

        self.assertIsNotNone(interface)

        # Ensure sound we are interested in exists
        self.assertIn('210871_synthping', self.mc.sounds)
        self.assertEqual(self.mc.sounds['210871_synthping'].priority, 1)
        self.assertEqual(self.mc.sounds['210871_synthping'].simultaneous_limit, 3)
        self.assertEqual(self.mc.sounds['210871_synthping'].stealing_method, SoundStealingMethod.oldest)
        self.assertEqual(self.mc.sounds['210871_synthping'].events_when_played, ['synthping_played'])
        self.assertIsNone(self.mc.sounds['210871_synthping'].events_when_stopped)
        self.assertEqual(self.mc.sounds['210871_synthping'].max_queue_time, 2.0)
        self.assertEqual(self.mc.sounds['210871_synthping'].mode_end_action, ModeEndAction.stop_looping)

        # Create sound instance with no overridden parameters (all values come from sound)
        instance1 = SoundInstance(self.mc.sounds['210871_synthping'])
        self.assertEqual(instance1.priority, 1)
        self.assertEqual(instance1.simultaneous_limit, 3)
        self.assertEqual(instance1.stealing_method, SoundStealingMethod.oldest)
        self.assertEqual(instance1.events_when_played, ['synthping_played'])
        self.assertIsNone(instance1.events_when_stopped)
        self.assertEqual(instance1.max_queue_time, 2.0)
        self.assertEqual(instance1.mode_end_action, ModeEndAction.stop_looping)

        # Create sound instance with several overridden parameters
        instance2 = SoundInstance(self.mc.sounds['210871_synthping'], None,
                                  {'priority': 5,
                                   'simultaneous_limit': 7,
                                   'stealing_method': 'skip',
                                   'events_when_played': ['use_sound_setting'],
                                   'events_when_stopped': ['synthping_stopped'],
                                   'max_queue_time': None,
                                   'mode_end_action': 'stop'})
        self.assertEqual(instance2.priority, 5)
        self.assertEqual(instance2.events_when_played, ['synthping_played'])
        self.assertEqual(instance2.events_when_stopped, ['synthping_stopped'])
        self.assertIsNone(instance2.max_queue_time)
        self.assertEqual(instance2.mode_end_action, ModeEndAction.stop)

        # These parameters may not be overridden (supplied values are ignored)
        self.assertEqual(instance2.simultaneous_limit, 3)
        self.assertEqual(instance2.stealing_method, SoundStealingMethod.oldest)

        # Create sound instance with several overridden parameters
        instance3 = SoundInstance(self.mc.sounds['210871_synthping'], None,
                                  {'priority': None,
                                   'events_when_played': None,
                                   'events_when_stopped': ['use_sound_setting'],
                                   'max_queue_time': 0.0})
        self.assertEqual(instance3.priority, 1)
        self.assertIsNone(instance3.events_when_played)
        self.assertIsNone(instance3.events_when_stopped)
        self.assertEqual(instance3.max_queue_time, 0.0)

    def test_mode_sounds(self):
        """ Test the sound system using sounds specified in a mode """

        if SoundSystem is None or self.mc.sound_system is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system is not enabled - skipping audio tests")
            self.skipTest("Sound system is not enabled")

        self.assertIsNotNone(self.mc.sound_system)
        interface = self.mc.sound_system.audio_interface
        if interface is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system audio interface could not be loaded - skipping audio tests")
            self.skipTest("Sound system audio interface could not be loaded")

        self.assertIsNotNone(interface)

        self.assertTrue(self.mc, 'sounds')

        # Mock BCP send method
        self.mc.bcp_processor.send = MagicMock()
        self.mc.bcp_processor.enabled = True

        # Get tracks
        track_sfx = interface.get_track_by_name("sfx")
        self.assertIsNotNone(track_sfx)
        self.assertEqual(track_sfx.name, "sfx")
        track_music = interface.get_track_by_name("music")
        self.assertIsNotNone(track_music)
        self.assertEqual(track_music.name, "music")

        self.assertIn('263774_music', self.mc.sounds)  # .wav
        music_sound = self.mc.sounds['263774_music']
        music_sound.load()

        # Allow some time for sound assets to load
        self.advance_real_time(2)

        # Start mode
        self.send(bcp_command='mode_start', name='mode2', priority=1000)
        self.assertTrue(self.mc.modes['mode2'].active)
        self.assertEqual(self.mc.modes['mode2'].priority, 1000)
        self.assertIn('boing_mode2', self.mc.sounds)  # .wav
        boing_sound = self.mc.sounds['boing_mode2']
        self.advance_real_time()

        # Play a longer music sound (launched by sound_player in mode2).  Will test
        # sound's mode_end_action when the mode ends.
        self.mc.events.post('play_sound_boing_in_mode2')
        self.advance_real_time()
        self.assertTrue(track_sfx.sound_is_playing(boing_sound))
        self.advance_real_time(1)

        self.mc.events.post('play_sound_music_fade_at_mode_end')
        self.advance_real_time(0.25)
        self.assertTrue(track_music.sound_is_playing(music_sound))
        self.advance_real_time(2)

        # End mode (sound should fade out for 1 second then stop)
        self.send(bcp_command='mode_stop', name='mode2')
        self.assertFalse(self.mc.modes['mode2'].active)
        self.advance_real_time()
        self.assertTrue(track_music.sound_is_playing(music_sound))
        self.advance_real_time(1.1)
        self.assertFalse(track_music.sound_is_playing(music_sound))

    def test_sound_fading(self):
        """ Tests the fading of sounds"""

        if SoundSystem is None or self.mc.sound_system is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system is not enabled - skipping audio tests")
            self.skipTest("Sound system is not enabled")

        self.assertIsNotNone(self.mc.sound_system)
        interface = self.mc.sound_system.audio_interface
        if interface is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system audio interface could not be loaded - skipping audio tests")
            self.skipTest("Sound system audio interface could not be loaded")

        self.assertIsNotNone(interface)

        track_music = interface.get_track_by_name("music")
        self.assertIsNotNone(track_music)
        self.assertEqual(track_music.name, "music")
        self.assertEqual(track_music.max_simultaneous_sounds, 1)

        self.advance_real_time(2)

        self.assertIn('263774_music', self.mc.sounds)       # .wav
        music = self.mc.sounds['263774_music']
        retry_count = 10
        while not music.loaded and retry_count > 0:
            if not music.loading:
                music.load()
            self.advance_real_time(0.5)
            retry_count -= 1

        self.assertTrue(music.loaded)
        instance1 = track_music.play_sound(music, context=None, settings={'fade_in': 2.0, 'volume': 1.0})
        self.advance_real_time()

        status = track_music.get_status()
        self.assertEqual(status[0]['sound_instance_id'], instance1.id)
        self.assertEqual(status[0]['status'], "playing")
        self.assertEqual(status[0]['fading_status'], "fade in")
        self.advance_real_time(2)

        instance1.stop(1)
        self.advance_real_time()
        status = track_music.get_status()
        self.assertEqual(status[0]['status'], "stopping")
        self.assertEqual(status[0]['fading_status'], "fade out")
        self.advance_real_time(1)
        status = track_music.get_status()
        self.assertEqual(status[0]['status'], "idle")

        instance2 = track_music.play_sound(music, context=None, settings={'fade_in': 0, 'volume': 1.0})
        self.advance_real_time(1)

        status = track_music.get_status()
        self.assertEqual(status[0]['sound_instance_id'], instance2.id)
        self.assertEqual(status[0]['status'], "playing")
        self.assertEqual(status[0]['fading_status'], "not fading")

        instance2.stop(0)
        self.advance_real_time(0.5)
        status = track_music.get_status()
        self.assertEqual(status[0]['status'], "idle")

    def test_sound_start_at(self):
        """ Tests starting a sound at a position other than the beginning"""

        if SoundSystem is None or self.mc.sound_system is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system is not enabled - skipping audio tests")
            self.skipTest("Sound system is not enabled")

        self.assertIsNotNone(self.mc.sound_system)
        interface = self.mc.sound_system.audio_interface
        if interface is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system audio interface could not be loaded - skipping audio tests")
            self.skipTest("Sound system audio interface could not be loaded")

        self.assertIsNotNone(interface)

        track_music = interface.get_track_by_name("music")
        self.assertIsNotNone(track_music)
        self.assertEqual(track_music.name, "music")
        self.assertEqual(track_music.max_simultaneous_sounds, 1)

        self.assertIn('263774_music', self.mc.sounds)  # .wav
        music_sound = self.mc.sounds['263774_music']
        music_sound.load()

        self.advance_real_time(2)

        self.assertTrue(music_sound.loaded)
        settings = {'start_at': 7.382}
        instance = self.mc.sounds['263774_music'].play(settings=settings)
        self.advance_real_time()
        status = track_music.get_status()
        self.assertGreaterEqual(status[0]['sample_pos'], interface.convert_seconds_to_buffer_length(7.382))
        self.advance_real_time(1)
        instance.stop(0.25)
        self.advance_real_time(0.3)

    def test_sound_instance_management(self):
        """ Tests instance management of sounds"""

        if SoundSystem is None or self.mc.sound_system is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system is not enabled - skipping audio tests")
            self.skipTest("Sound system is not enabled")

        self.assertIsNotNone(self.mc.sound_system)
        interface = self.mc.sound_system.audio_interface
        if interface is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system audio interface could not be loaded - skipping audio tests")
            self.skipTest("Sound system audio interface could not be loaded")

        self.assertIsNotNone(interface)

        # Mock BCP send method
        self.mc.bcp_processor.send = MagicMock()
        self.mc.bcp_processor.enabled = True

        track_sfx = interface.get_track_by_name("sfx")
        self.assertIsNotNone(track_sfx)
        self.assertEqual(track_sfx.name, "sfx")
        self.assertEqual(track_sfx.max_simultaneous_sounds, 8)
        self.advance_real_time()

        # Test skip stealing method
        self.assertIn('264828_text', self.mc.sounds)  # .wav
        text_sound = self.mc.sounds['264828_text']
        if not text_sound.loaded:
            if not text_sound.loading:
                text_sound.load()
            self.advance_real_time(1)

        self.assertEqual(text_sound.simultaneous_limit, 3)
        if SoundStealingMethod is not None:
            self.assertEqual(text_sound.stealing_method, SoundStealingMethod.skip)

        instance1 = text_sound.play(settings={'loops': 0, 'events_when_played': ['instance1_played']})
        instance2 = text_sound.play(settings={'loops': 0, 'events_when_played': ['instance2_played']})
        instance3 = text_sound.play(settings={'loops': 0, 'events_when_played': ['instance3_played']})
        instance4 = text_sound.play(settings={'loops': 0, 'events_when_played': ['instance4_played']})
        instance5 = text_sound.play(settings={'loops': 0, 'events_when_played': ['instance5_played']})

        self.advance_real_time(0.5)

        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='instance1_played')
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='instance2_played')
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='instance3_played')
        with self.assertRaises(AssertionError):
            self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='instance4_played')
            self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='instance5_played')

        self.assertTrue(instance1.played)
        self.assertTrue(instance2.played)
        self.assertTrue(instance3.played)
        self.assertIsNone(instance4)
        self.assertIsNone(instance5)

        track_sfx.stop_all_sounds()
        self.advance_real_time()

        # Test oldest stealing method
        self.mc.bcp_processor.send.reset_mock()
        self.assertIn('210871_synthping', self.mc.sounds)  # .wav
        synthping = self.mc.sounds['210871_synthping']
        if not synthping.loaded:
            if not synthping.loading:
                synthping.load()
            self.advance_real_time(1)
        self.assertEqual(synthping.simultaneous_limit, 3)
        if SoundStealingMethod is not None:
            self.assertEqual(synthping.stealing_method, SoundStealingMethod.oldest)

        synthping_instance1 = synthping.play(settings={'events_when_played': ['synthping_instance1_played'],
                                                       'events_when_stopped': ['synthping_instance1_stopped']})
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_has_calls([call('trigger', sound_instance=ANY, name='synthping_instance1_played')])

        synthping_instance2 = synthping.play(settings={'events_when_played': ['synthping_instance2_played'],
                                                       'events_when_stopped': ['synthping_instance2_stopped']})
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_has_calls([call('trigger', sound_instance=ANY, name='synthping_instance1_played'),
                                                     call('trigger', sound_instance=ANY, name='synthping_instance2_played')])

        synthping_instance3 = synthping.play(settings={'events_when_played': ['synthping_instance3_played'],
                                                       'events_when_stopped': ['synthping_instance3_stopped']})
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_has_calls([call('trigger', sound_instance=ANY, name='synthping_instance1_played'),
                                                     call('trigger', sound_instance=ANY, name='synthping_instance2_played'),
                                                     call('trigger', sound_instance=ANY, name='synthping_instance3_played')])

        synthping_instance4 = synthping.play(settings={'events_when_played': ['synthping_instance4_played'],
                                                       'events_when_stopped': ['synthping_instance4_stopped']})
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_has_calls([call('trigger', sound_instance=ANY, name='synthping_instance1_played'),
                                                     call('trigger', sound_instance=ANY, name='synthping_instance2_played'),
                                                     call('trigger', sound_instance=ANY, name='synthping_instance3_played'),
                                                     call('trigger', sound_instance=ANY, name='synthping_instance1_stopped'),
                                                     call('trigger', sound_instance=ANY, name='synthping_instance4_played')])

        synthping_instance5 = synthping.play(settings={'events_when_played': ['synthping_instance5_played'],
                                                       'events_when_stopped': ['synthping_instance5_stopped']})
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_has_calls([call('trigger', sound_instance=ANY, name='synthping_instance1_played'),
                                                     call('trigger', sound_instance=ANY, name='synthping_instance2_played'),
                                                     call('trigger', sound_instance=ANY, name='synthping_instance3_played'),
                                                     call('trigger', sound_instance=ANY, name='synthping_instance1_stopped'),
                                                     call('trigger', sound_instance=ANY, name='synthping_instance4_played'),
                                                     call('trigger', sound_instance=ANY, name='synthping_instance2_stopped'),
                                                     call('trigger', sound_instance=ANY, name='synthping_instance5_played')])

        self.assertTrue(synthping_instance1.played)
        self.assertTrue(synthping_instance2.played)
        self.assertTrue(synthping_instance3.played)
        self.assertTrue(synthping_instance4.played)
        self.assertTrue(synthping_instance5.played)

        track_sfx.stop_all_sounds()
        self.advance_real_time()

        # Test newest stealing method
        self.mc.bcp_processor.send.reset_mock()
        self.assertIn('198361_sfx-028', self.mc.sounds)  # .wav
        sfx = self.mc.sounds['198361_sfx-028']
        if not sfx.loaded:
            if not sfx.loading:
                sfx.load()
            self.advance_real_time(1)
        self.assertEqual(sfx.simultaneous_limit, 3)
        if SoundStealingMethod is not None:
            self.assertEqual(sfx.stealing_method, SoundStealingMethod.newest)

        sfx_instance1 = sfx.play(
            settings={'events_when_played': ['sfx_instance1_played'], 'events_when_stopped': ['sfx_instance1_stopped']})
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_has_calls([call('trigger', sound_instance=ANY, name='sfx_instance1_played')])

        sfx_instance2 = sfx.play(
            settings={'events_when_played': ['sfx_instance2_played'], 'events_when_stopped': ['sfx_instance2_stopped']})
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_has_calls([call('trigger', sound_instance=ANY, name='sfx_instance1_played'),
                                                     call('trigger', sound_instance=ANY, name='sfx_instance2_played')])

        sfx_instance3 = sfx.play(
            settings={'events_when_played': ['sfx_instance3_played'], 'events_when_stopped': ['sfx_instance3_stopped']})
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_has_calls([call('trigger', sound_instance=ANY, name='sfx_instance1_played'),
                                                     call('trigger', sound_instance=ANY, name='sfx_instance2_played'),
                                                     call('trigger', sound_instance=ANY, name='sfx_instance3_played')])

        sfx_instance4 = sfx.play(
            settings={'events_when_played': ['sfx_instance4_played'], 'events_when_stopped': ['sfx_instance4_stopped']})
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_has_calls([call('trigger', sound_instance=ANY, name='sfx_instance1_played'),
                                                     call('trigger', sound_instance=ANY, name='sfx_instance2_played'),
                                                     call('trigger', sound_instance=ANY, name='sfx_instance3_played'),
                                                     call('trigger', sound_instance=ANY, name='sfx_instance3_stopped'),
                                                     call('trigger', sound_instance=ANY, name='sfx_instance4_played')])

        sfx_instance5 = sfx.play(
            settings={'events_when_played': ['sfx_instance5_played'], 'events_when_stopped': ['sfx_instance5_stopped']})
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_has_calls([call('trigger', sound_instance=ANY, name='sfx_instance1_played'),
                                                     call('trigger', sound_instance=ANY, name='sfx_instance2_played'),
                                                     call('trigger', sound_instance=ANY, name='sfx_instance3_played'),
                                                     call('trigger', sound_instance=ANY, name='sfx_instance3_stopped'),
                                                     call('trigger', sound_instance=ANY, name='sfx_instance4_played'),
                                                     call('trigger', sound_instance=ANY, name='sfx_instance4_stopped'),
                                                     call('trigger', sound_instance=ANY, name='sfx_instance5_played')])

        self.assertTrue(sfx_instance1.played)
        self.assertTrue(sfx_instance2.played)
        self.assertTrue(sfx_instance3.played)
        self.assertTrue(sfx_instance4.played)
        self.assertTrue(sfx_instance5.played)

        # Stop all sounds playing on the sfx track to start the next test
        track_sfx.stop_all_sounds()
        self.advance_real_time()
        self.mc.bcp_processor.send.reset_mock()
        self.assertEqual(track_sfx.get_sound_players_in_use_count(), 0)
        self.assertEqual(track_sfx.get_sound_queue_count(), 0)

        # Test simultaneous_limit in sound group (skip stealing method)
        self.assertIn('drum_group', self.mc.sounds)
        drum_group = self.mc.sounds['drum_group']
        self.assertEqual(drum_group.simultaneous_limit, 3)
        if SoundStealingMethod is not None:
            self.assertEqual(drum_group.stealing_method, SoundStealingMethod.skip)

        drum_group_instance1 = drum_group.play(settings={'events_when_played': ['drum_group_instance1_played']})
        drum_group_instance2 = drum_group.play(settings={'events_when_played': ['drum_group_instance2_played']})
        drum_group_instance3 = drum_group.play(settings={'events_when_played': ['drum_group_instance3_played']})
        drum_group_instance4 = drum_group.play(settings={'events_when_played': ['drum_group_instance4_played']})
        drum_group_instance5 = drum_group.play(settings={'events_when_played': ['drum_group_instance5_played']})
        self.advance_real_time()

        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='drum_group_instance1_played')
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='drum_group_instance2_played')
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='drum_group_instance3_played')
        with self.assertRaises(AssertionError):
            self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='drum_group_instance4_played')
            self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='drum_group_instance5_played')

        self.assertTrue(drum_group_instance1.played)
        self.assertTrue(drum_group_instance2.played)
        self.assertTrue(drum_group_instance3.played)
        self.assertIsNone(drum_group_instance4)
        self.assertIsNone(drum_group_instance5)

    def test_sound_player_parameters(self):
        """ Tests sound parameters overridden in the sound_player"""

        if SoundSystem is None or self.mc.sound_system is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system is not enabled - skipping audio tests")
            self.skipTest("Sound system is not enabled")

        self.assertIsNotNone(self.mc.sound_system)
        interface = self.mc.sound_system.audio_interface
        if interface is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system audio interface could not be loaded - skipping audio tests")
            self.skipTest("Sound system audio interface could not be loaded")

        self.assertIsNotNone(interface)

        # Mock BCP send method
        self.mc.bcp_processor.send = MagicMock()
        self.mc.bcp_processor.enabled = True

        track_sfx = interface.get_track_by_name("sfx")
        self.assertIsNotNone(track_sfx)
        self.assertEqual(track_sfx.name, "sfx")
        self.assertEqual(track_sfx.max_simultaneous_sounds, 8)

        self.advance_real_time(1)

        self.assertIn('264828_text', self.mc.sounds)  # .wav
        text_sound = self.mc.sounds['264828_text']

        # Test sound played from sound_player with all default parameter values
        self.mc.events.post('play_sound_text_default_params')
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='text_sound_played')
        status = track_sfx.get_status()
        self.assertEqual(status[0]['sound_id'], text_sound.id)
        instance_id = status[0]['sound_instance_id']
        text_sound_instance = track_sfx.get_playing_sound_instance_by_id(instance_id)
        self.assertIsNotNone(text_sound_instance)
        self.assertEqual(text_sound_instance.volume, 0.5)
        self.assertEqual(text_sound_instance.loops, 7)
        self.assertEqual(text_sound_instance.priority, 0)
        self.assertEqual(text_sound_instance.start_at, 0)
        self.assertEqual(text_sound_instance.fade_out, 0)
        self.assertEqual(text_sound_instance.fade_out, 0)
        self.assertIsNone(text_sound_instance.max_queue_time)
        self.assertEqual(text_sound_instance.simultaneous_limit, 3)

        track_sfx.stop_all_sounds()
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='text_sound_stopped')

        # Now test sound played from sound_player with overridden parameter values
        self.mc.events.post('play_sound_text_param_set_1')
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='text_sound_played_param_set_1')
        status = track_sfx.get_status()
        self.assertEqual(status[0]['sound_id'], text_sound.id)
        instance_id = status[0]['sound_instance_id']
        text_sound_instance = track_sfx.get_playing_sound_instance_by_id(instance_id)
        self.assertIsNotNone(text_sound_instance)
        self.assertEqual(text_sound_instance.volume, 0.67)
        self.assertEqual(text_sound_instance.loops, 2)
        self.assertEqual(text_sound_instance.priority, 1000)
        self.assertEqual(text_sound_instance.start_at, 0.05)
        self.assertEqual(text_sound_instance.fade_in, 0.25)
        self.assertEqual(text_sound_instance.fade_out, 0.1)
        self.assertEqual(text_sound_instance.max_queue_time, 0.15)
        self.assertEqual(text_sound_instance.simultaneous_limit, 3)

        track_sfx.stop_all_sounds()
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='text_sound_stopped_param_set_1')

    def test_track_player(self):
        """Tests the track_player"""

        if SoundSystem is None or self.mc.sound_system is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system is not enabled - skipping audio tests")
            self.skipTest("Sound system is not enabled")

        # Mock BCP send method
        self.mc.bcp_processor.send = MagicMock()
        self.mc.bcp_processor.enabled = True

        self.assertIsNotNone(self.mc.sound_system)
        interface = self.mc.sound_system.audio_interface
        if interface is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system audio interface could not be loaded - skipping audio tests")
            self.skipTest("Sound system audio interface could not be loaded")

        self.assertIsNotNone(interface)

        track_music = interface.get_track_by_name("music")
        self.assertIsNotNone(track_music)
        self.assertEqual(track_music.name, "music")
        self.assertEqual(track_music.max_simultaneous_sounds, 1)

        self.advance_real_time(1)

        self.assertIn('263774_music', self.mc.sounds)  # .wav
        sound_music = self.mc.sounds['263774_music']
        self.assertFalse(sound_music.loaded)

        self.mc.events.post('load_music')
        self.advance_real_time(2)
        self.assertTrue(sound_music.loaded)

        # TODO: Improve test (need some automated status checks for track control)
        instance = sound_music.play()
        self.advance_real_time(2)
        self.mc.events.post('pause_music_track')
        self.advance_real_time(2)
        self.mc.bcp_processor.send.assert_any_call('trigger', track='music', name='music_track_paused')
        self.mc.bcp_processor.send.reset_mock()

        self.mc.events.post('resume_music_track')
        self.advance_real_time(2)
        self.mc.bcp_processor.send.assert_any_call('trigger', track='music', name='music_track_played')
        self.mc.bcp_processor.send.assert_any_call('trigger', track='music', name='keep_going')
        self.mc.bcp_processor.send.reset_mock()

        self.mc.events.post('stop_all_tracks')
        self.advance_real_time(2)
        self.mc.bcp_processor.send.assert_any_call('trigger', track='music', name='music_track_stopped')
        self.mc.bcp_processor.send.reset_mock()

        self.mc.events.post('play_music_track')
        self.advance_real_time(1)
        self.mc.bcp_processor.send.assert_any_call('trigger', track='music', name='music_track_played')
        self.mc.bcp_processor.send.reset_mock()

        instance = self.mc.sounds['263774_music'].play()
        self.advance_real_time(2)
        self.mc.events.post('set_music_track_volume_quiet')
        self.advance_real_time(2)
        self.mc.events.post('set_music_track_volume_loud')
        self.advance_real_time(2)
        self.mc.events.post('stop_all_sounds_on_music_track')
        self.advance_real_time(1)

        self.assertTrue(sound_music.loaded)
        self.mc.events.post('unload_music')
        self.advance_real_time()
        self.assertFalse(sound_music.loaded)

        def test_sound_looping(self):
            """ Tests the sound looping features """

            if SoundSystem is None or self.mc.sound_system is None:
                log = logging.getLogger('TestAudio')
                log.warning("Sound system is not enabled - skipping audio tests")
                self.skipTest("Sound system is not enabled")

            self.assertIsNotNone(self.mc.sound_system)
            interface = self.mc.sound_system.audio_interface
            if interface is None:
                log = logging.getLogger('TestAudio')
                log.warning("Sound system audio interface could not be loaded - skipping audio tests")
                self.skipTest("Sound system audio interface could not be loaded")

            self.assertIsNotNone(interface)

            # Mock BCP send method
            self.mc.bcp_processor.send = MagicMock()
            self.mc.bcp_processor.enabled = True

            track_music = interface.get_track_by_name("music")
            self.assertIsNotNone(track_music)
            self.assertEqual(track_music.name, "music")
            self.assertEqual(track_music.max_simultaneous_sounds, 1)

            # Because these tests can be run at different audio settings depending upon hardware,
            # sample lengths and positions in bytes are not reliable to compare for testing. This
            # test will convert sample lengths/positions back to time for comparisons based on the
            # audio interface settings actually used in the test.
            settings = self.mc.sound_system.audio_interface.get_settings()
            self.assertIsNotNone(settings)
            seconds_to_bytes_factor = settings['seconds_to_bytes_factor']

            self.advance_real_time(1)

            self.assertIn('looptest', self.mc.sounds)  # .wav
            sound_looptest = self.mc.sounds['looptest']
            self.assertFalse(sound_looptest.loaded)
            self.assertAlmostEqual(sound_looptest.loop_start_at, 1.8461538, 4)
            self.assertAlmostEqual(sound_looptest.loop_end_at, 3.6923077, 4)
            self.assertEqual(sound_looptest.loops, 3)

            instance1 = track_music.play_sound(sound_looptest, context=None, settings={'volume': 1.0})
            self.advance_real_time()

            status = track_music.get_status()
            self.assertEqual(status[0]['sound_instance_id'], instance1.id)
            self.assertEqual(status[0]['sound_id'], sound_looptest.id)
            self.assertEqual(status[0]['status'], "playing")
            self.assertEqual(status[0]['current_loop'], 0)
            self.assertEqual(status[0]['loops'], 3)
            self.assertAlmostEqual(status[0]['loop_start_pos'] / seconds_to_bytes_factor, 1.8461538, 4)
            self.assertAlmostEqual(status[0]['loop_end_pos'] / seconds_to_bytes_factor, 3.6923077, 4)
            self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='looptest_played')
            self.mc.bcp_processor.send.reset_mock()

            self.advance_real_time(10)
            instance1.stop()
            self.advance_real_time()

            status = track_music.get_status()
            self.assertEqual(status[0]['sound_instance_id'], instance1.id)
            self.assertEqual(status[0]['current_loop'], 3)
            self.assertEqual(status[0]['loops'], 0)
            self.assertAlmostEqual(status[0]['loop_start_pos'] / seconds_to_bytes_factor, 1.8461538, 4)
            self.assertAlmostEqual(status[0]['loop_end_pos'] / seconds_to_bytes_factor, 5.8846259, 4)

            self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='looptest_looping')
            self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='looptest_stopped')

            # Now start playing the song after the end of the loop end (should loop back to the beginning of the loop)
            instance1 = track_music.play_sound(sound_looptest, context=None,
                                               settings={'volume': 1.0, 'start_at': 3.8, 'loops': 5})
            self.advance_real_time()

            status = track_music.get_status()
            self.assertEqual(status[0]['sound_instance_id'], instance1.id)
            self.assertEqual(status[0]['sound_id'], sound_looptest.id)
            self.assertEqual(status[0]['status'], "playing")
            self.assertEqual(status[0]['current_loop'], 0)
            self.assertEqual(status[0]['loops'], 5)
            self.assertGreater(status[0]['sample_pos'] / seconds_to_bytes_factor, 3.8)
            self.assertAlmostEqual(status[0]['loop_start_pos'] / seconds_to_bytes_factor, 1.8461538, 4)
            self.assertAlmostEqual(status[0]['loop_end_pos'] / seconds_to_bytes_factor, 3.6923077, 4)
            self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='looptest_played')
            self.mc.bcp_processor.send.reset_mock()

            self.advance_real_time(2.5)

            status = track_music.get_status()
            self.assertEqual(status[0]['sound_instance_id'], instance1.id)
            self.assertEqual(status[0]['current_loop'], 1)
            self.assertEqual(status[0]['loops'], 4)
            self.assertGreater(status[0]['sample_pos'] / seconds_to_bytes_factor, 1.8461538)
            self.assertLess(status[0]['sample_pos'] / seconds_to_bytes_factor, 5.8846259)
            self.assertAlmostEqual(status[0]['loop_start_pos'] / seconds_to_bytes_factor, 1.8461538, 4)
            self.assertAlmostEqual(status[0]['loop_end_pos'] / seconds_to_bytes_factor, 3.6923077, 4)

            instance1.stop()
            self.advance_real_time()

            self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='looptest_looping')
            self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='looptest_stopped')
            self.mc.bcp_processor.send.reset_mock()

            # Now test a voice-stealing scenario to ensure sound settings are copied correctly
            track_voice = interface.get_track_by_name("voice")
            self.assertIsNotNone(track_voice)
            self.assertEqual(track_voice.name, "voice")
            self.assertEqual(track_voice.max_simultaneous_sounds, 1)

            self.assertIn('104457_moron_test', self.mc.sounds)
            sound_moron_test = self.mc.sounds['104457_moron_test']

            instance2 = track_voice.play_sound(sound_moron_test, context=None,
                                               settings={'volume': 1.0, 'loops': 0, 'priority': 900})
            self.advance_real_time()

            status = track_voice.get_status()
            self.assertEqual(status[0]['sound_instance_id'], instance2.id)
            self.assertEqual(status[0]['sound_id'], sound_moron_test.id)
            self.assertEqual(status[0]['status'], "playing")
            self.assertEqual(status[0]['current_loop'], 0)
            self.assertEqual(status[0]['loops'], 0)
            self.assertAlmostEqual(status[0]['loop_start_pos'] / seconds_to_bytes_factor, 0.0, 3)
            self.assertAlmostEqual(status[0]['loop_end_pos'] / seconds_to_bytes_factor, 7.39048, 3)
            self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='moron_test_played')
            self.mc.bcp_processor.send.reset_mock()

            self.advance_real_time(1.0)

            self.assertIn('113690_test', self.mc.sounds)
            sound_test = self.mc.sounds['113690_test']

            # Play sound with higher priority than the one currently playing to make sure the sound replacing
            # code copies all the sound settings to the new sound (this test specifically addresses a bug
            # introduced after adding loop point settings).
            instance3 = track_voice.play_sound(sound_test, context=None,
                                               settings={'volume': 1.0, 'loops': 0, 'priority': 1000})
            self.advance_real_time(0.2)

            status = track_voice.get_status()
            self.assertEqual(status[0]['sound_instance_id'], instance3.id)
            self.assertEqual(status[0]['sound_id'], sound_test.id)
            self.assertEqual(status[0]['status'], "playing")
            self.assertEqual(status[0]['current_loop'], 0)
            self.assertEqual(status[0]['loops'], 0)
            self.assertAlmostEqual(status[0]['loop_start_pos'] / seconds_to_bytes_factor, 0.0, 3)
            self.assertAlmostEqual(status[0]['loop_end_pos'] / seconds_to_bytes_factor, 6.95655, 3)

        # TODO: Add integration test for sound_player
        # TODO: Add integration test for track_player

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

    def test_sound_player_blocking(self):
        """ Tests blocking in the sound_player."""

        if SoundSystem is None or self.mc.sound_system is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system is not enabled - skipping audio tests")
            self.skipTest("Sound system is not enabled")

        self.assertIsNotNone(self.mc.sound_system)
        interface = self.mc.sound_system.audio_interface
        if interface is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system audio interface could not be loaded - skipping audio tests")
            self.skipTest("Sound system audio interface could not be loaded")

        self.assertIsNotNone(interface)

        # Mock BCP send method
        self.mc.bcp_processor.send = MagicMock()
        self.mc.bcp_processor.enabled = True

        # Get tracks
        track_sfx = interface.get_track_by_name("sfx")
        self.assertIsNotNone(track_sfx)
        self.assertEqual(track_sfx.name, "sfx")

        # Start mode 1 (lower priority mode)
        self.send(bcp_command='mode_start', name='mode1', priority=500)
        self.assertTrue(self.mc.modes['mode1'].active)
        self.assertEqual(self.mc.modes['mode1'].priority, 500)
        self.assertIn('210871_synthping', self.mc.sounds)
        self.advance_real_time()

        # Play a sound with an event
        self.mc.events.post('play_slingshot_sound')
        self.advance_real_time()
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='synthping_played')
        self.mc.bcp_processor.send.reset_mock()

        # Start mode 2 (higher priority mode)
        self.send(bcp_command='mode_start', name='mode2', priority=1000)
        self.assertTrue(self.mc.modes['mode2'].active)
        self.assertEqual(self.mc.modes['mode2'].priority, 1000)
        self.assertIn('boing_mode2', self.mc.sounds)
        self.advance_real_time()

        # Play a sound with an event (both modes should play a sound)
        self.mc.events.post('play_slingshot_sound')
        self.advance_real_time()
        self.assertEqual(2, self.mc.bcp_processor.send.call_count)
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='boing_sound_played')
        self.mc.bcp_processor.send.assert_any_call('trigger', sound_instance=ANY, name='synthping_played')
        self.mc.bcp_processor.send.reset_mock()

        # Play the same sounds using an event that uses blocking (only the highest priority mode should play a sound)
        self.mc.events.post('play_slingshot_sound_with_block')
        self.advance_real_time()
        self.assertEqual(1, self.mc.bcp_processor.send.call_count)
        self.mc.bcp_processor.send.assert_called_once_with('trigger', sound_instance=ANY, name='boing_sound_played')
        self.mc.bcp_processor.send.reset_mock()

        # Play the same sounds using an event that uses blocking (only the highest priority mode should play a sound)
        self.mc.events.post('play_slingshot_sound_with_express_config_block')
        self.advance_real_time()
        self.assertEqual(1, self.mc.bcp_processor.send.call_count)
        self.mc.bcp_processor.send.assert_called_once_with('trigger', sound_instance=ANY, name='boing_sound_played')
        self.mc.bcp_processor.send.reset_mock()

        # End mode 1
        self.send(bcp_command='mode_stop', name='mode1')
        self.assertFalse(self.mc.modes['mode1'].active)
        self.advance_real_time()
