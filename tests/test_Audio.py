from tests.MpfMcTestCase import MpfMcTestCase
from kivy.logger import Logger


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
            Logger.warning("Sound system is not enabled - unable to run audio tests")
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

        # Allow some time for sound assets to load
        self.advance_time(2)

        # /sounds/sfx
        self.assertIn('198361_sfx-028', self.mc.sounds)     # .wav
        self.assertIn('210871_synthping', self.mc.sounds)   # .wav
        self.assertIn('264828_text', self.mc.sounds)        # .ogg

        # /sounds/voice
        self.assertIn('104457_moron_test', self.mc.sounds)  # .wav
        self.assertIn('113690_test', self.mc.sounds)        # .wav
        self.assertIn('170380_clear', self.mc.sounds)       # .flac

        # /sounds/music
        self.assertIn('263774_music', self.mc.sounds)       # .wav

        # Test sound_player
        self.mc.events.post('play_sound_text')
        self.mc.events.post('play_sound_music')
        self.advance_time(1)

        # Test two sounds at the same time on the voice track (only
        # 1 sound at a time max).  Second sound should be queued and
        # play immediately after the first one ends.
        self.mc.events.post('play_sound_test')
        self.advance_time(2)
        self.mc.events.post('play_sound_moron_test')
        self.advance_time(3)
        self.mc.events.post('play_sound_synthping')
        self.advance_time(3)
        self.mc.events.post('play_sound_synthping')
        self.advance_time(10)

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
        # Play two sounds on track with max_simultaneous_sounds = 1 (test sound queue, time expiration, priority scenarios)
        # Play a sound on each track simultaneously
        # Stop all sounds on track
        # Stop all sounds on all tracks
        # Ducking
        # Configuration file tests (audio interface, tracks, sounds, sound player, sound trigger events, etc.)
        #
        """
