import logging

from mpfmc.tests.MpfMcTestCase import MpfMcTestCase
from unittest.mock import MagicMock, call
from mpfmc.config_collections.playlist import PlaylistInstance

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

        playlist_controller = interface.get_playlist_controller("playlist")
        self.assertIsNotNone(playlist_controller)
        self.assertEqual(playlist_controller.name, "playlist")
        self.assertEqual(playlist_controller.crossfade_time, 2.0)

        # /sounds/playlist
        self.assertTrue(hasattr(self.mc, 'sounds'))
        self.assertIn('drumbeat_7', self.mc.sounds)
        self.assertIn('hippie_ahead', self.mc.sounds)
        self.assertIn('rainbow_disco_bears', self.mc.sounds)
        self.assertIn('dirty_grinding_beat_loop', self.mc.sounds)

        # Playlists
        self.assertTrue(hasattr(self.mc, 'playlists'))
        self.assertIn('attract_music', self.mc.playlists)
        self.assertListEqual(['drumbeat_7', 'hippie_ahead', 'rainbow_disco_bears', 'dirty_grinding_beat_loop'],
                             self.mc.playlists['attract_music']['sounds'])

        # Create a PlaylistInstance to manipulate directly for testing
        attract_music_playlist = PlaylistInstance('attract_music',
                                                  self.mc.playlists['attract_music'],
                                                  playlist_controller.crossfade_time)
        self.assertIsNotNone(attract_music_playlist)
        self.assertFalse(attract_music_playlist.repeat)

        # Advance through the playlist
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertEqual('drumbeat_7', current_sound)
        self.assertFalse(attract_music_playlist.end_of_playlist)
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertEqual('hippie_ahead', current_sound)
        self.assertFalse(attract_music_playlist.end_of_playlist)
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertEqual('rainbow_disco_bears', current_sound)
        self.assertFalse(attract_music_playlist.end_of_playlist)
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertEqual('dirty_grinding_beat_loop', current_sound)
        self.assertTrue(attract_music_playlist.end_of_playlist)
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertIsNone(current_sound)

        # Create another PlaylistInstance, this time enable repeat
        attract_music_playlist = PlaylistInstance('attract_music',
                                                  self.mc.playlists['attract_music'],
                                                  playlist_controller.crossfade_time,
                                                  settings={'repeat': True})
        self.assertIsNotNone(attract_music_playlist)
        self.assertTrue(attract_music_playlist.repeat)

        # Advance through the playlist
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertEqual('drumbeat_7', current_sound)
        self.assertFalse(attract_music_playlist.end_of_playlist)
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertEqual('hippie_ahead', current_sound)
        self.assertFalse(attract_music_playlist.end_of_playlist)
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertEqual('rainbow_disco_bears', current_sound)
        self.assertFalse(attract_music_playlist.end_of_playlist)
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertEqual('dirty_grinding_beat_loop', current_sound)
        self.assertTrue(attract_music_playlist.end_of_playlist)
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertEqual('drumbeat_7', current_sound)
        self.assertFalse(attract_music_playlist.end_of_playlist)

        # Test playlist_player
        self.advance_time()
        self.mc.events.post('play_attract_music')
        self.advance_real_time(1)

        status = track_playlist.get_status()
        self.assertEqual(status[0]['status'], "playing")
        self.assertEqual(status[0]['sound_id'], self.mc.sounds["drumbeat_7"].id)
        self.assertEqual(status[1]['status'], "idle")
        self.advance_real_time(2)

        self.mc.events.post('advance_playlist')
        self.advance_real_time(10)

