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


class TestAudioPlaylist(MpfMcTestCase):
    """
    """
    def get_machine_path(self):
        return 'tests/machine_files/audio'

    def get_config_file(self):
        return 'test_audio_playlist.yaml'

    def test_playlist_track(self):
        """ Tests the Playlist track type and its associated assets"""

        if SoundSystem is None or self.mc.sound_system is None:
            log = logging.getLogger('TestAudioPlaylist')
            log.warning("Sound system is not enabled - skipping audio tests")
            self.skipTest("Sound system is not enabled")

        self.assertIsNotNone(self.mc.sound_system)
        interface = self.mc.sound_system.audio_interface
        if interface is None:
            log = logging.getLogger('TestAudioPlaylist')
            log.warning("Sound system audio interface could not be loaded - skipping audio tests")
            self.skipTest("Sound system audio interface could not be loaded")

        self.assertIsNotNone(interface)

        # Check playlist track
        track_playlist = interface.get_track_by_name("playlist")
        self.assertIsNotNone(track_playlist)
        self.assertEqual(track_playlist.name, "playlist")
        self.assertAlmostEqual(track_playlist.volume, 0.6, 1)

        # /sounds/playlist
        self.assertTrue(hasattr(self.mc, 'sounds'))
        self.assertIn('kick', self.mc.sounds)
        self.assertIn('kick2', self.mc.sounds)
        self.assertIn('hihat', self.mc.sounds)
        self.assertIn('snare', self.mc.sounds)
        self.assertIn('clap', self.mc.sounds)
        self.assertIn('bass_synth', self.mc.sounds)

        # Playlists
        self.assertTrue(hasattr(self.mc, 'playlists'))
        self.assertIn('basic_beat', self.mc.playlists)
        self.assertIn('basic_beat2', self.mc.playlists)

        # Test playlist_player
        self.advance_time()
        self.mc.events.post('play_sound_synthping')
        self.mc.events.post('play_basic_beat')
        self.advance_real_time(1)

        self.mc.events.post('add_hi_hats')
        self.advance_time()
        self.advance_real_time(3)

        self.mc.events.post('add_snare')
        self.mc.events.post('add_claps')
        self.advance_real_time(2)
        status = track_playlist.get_status()
        self.assertEqual(status[0]['status'], "playing")
        self.assertEqual(status[0]['sound_id'], self.mc.sounds["kick"].id)
        self.assertTrue(status[0]['looping'])
        self.assertEqual(len(status[0]['layers']), 3)
        self.assertEqual(status[1]['status'], "idle")
        self.advance_real_time(2)

        self.mc.events.post('play_basic_beat2')
        self.advance_real_time(4)
        status = track_playlist.get_status()
        self.assertEqual(status[0]['status'], "playing")
        self.assertEqual(status[0]['sound_id'], self.mc.sounds["kick2"].id)
        self.assertTrue(status[0]['looping'])
        self.assertEqual(len(status[0]['layers']), 4)

        self.mc.events.post('fade_out_bass_synth')
        self.advance_real_time(4)

        self.mc.events.post('stop_current_loop')
        self.mc.events.post('play_sound_synthping')
        self.advance_real_time(2)
