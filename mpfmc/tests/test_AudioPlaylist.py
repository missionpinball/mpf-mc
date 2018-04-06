import logging

from mpfmc.tests.MpfMcTestCase import MpfMcTestCase
from unittest.mock import MagicMock, call, ANY
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
        self.assertEqual("playlist", track_playlist.name)
        self.assertAlmostEqual(0.6, track_playlist.volume, 1)

        playlist_controller = interface.get_playlist_controller("playlist")
        self.assertIsNotNone(playlist_controller)
        self.assertEqual("playlist", playlist_controller.name)
        self.assertEqual(2.0, playlist_controller.crossfade_time)

        # /sounds/playlist
        self.assertTrue(hasattr(self.mc, 'sounds'))
        self.assertIn('drumbeat_7', self.mc.sounds)
        self.assertIn('hippie_ahead', self.mc.sounds)
        self.assertIn('rainbow_disco_bears', self.mc.sounds)
        self.assertIn('dirty_grinding_beat_loop', self.mc.sounds)

        # Playlists
        self.assertTrue(hasattr(self.mc, 'playlists'))
        self.assertIn('attract_music', self.mc.playlists)
        self.assertListEqual(['drumbeat_7', 'rainbow_disco_bears', 'dirty_grinding_beat_loop', 'hippie_ahead'],
                             self.mc.playlists['attract_music']['sounds'])

        # Create a PlaylistInstance to manipulate directly for testing
        attract_music_playlist = PlaylistInstance('attract_music',
                                                  self.mc.playlists['attract_music'],
                                                  playlist_controller.crossfade_time,
                                                  settings={
                                                      "crossfade_mode": "override",
                                                      "crossfade_time": 1.5
                                                  })
        self.assertIsNotNone(attract_music_playlist)
        self.assertFalse(attract_music_playlist.repeat)
        self.assertEqual(1.5, attract_music_playlist.crossfade_time)

        # Advance through the playlist
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertEqual('drumbeat_7', current_sound)
        self.assertFalse(attract_music_playlist.end_of_playlist)
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertEqual('rainbow_disco_bears', current_sound)
        self.assertFalse(attract_music_playlist.end_of_playlist)
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertEqual('dirty_grinding_beat_loop', current_sound)
        self.assertFalse(attract_music_playlist.end_of_playlist)
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertEqual('hippie_ahead', current_sound)
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
        self.assertEqual('rainbow_disco_bears', current_sound)
        self.assertFalse(attract_music_playlist.end_of_playlist)
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertEqual('dirty_grinding_beat_loop', current_sound)
        self.assertFalse(attract_music_playlist.end_of_playlist)
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertEqual('hippie_ahead', current_sound)
        self.assertTrue(attract_music_playlist.end_of_playlist)
        current_sound = attract_music_playlist.get_next_sound_name()
        self.assertEqual('drumbeat_7', current_sound)
        self.assertFalse(attract_music_playlist.end_of_playlist)

        # Mock BCP send method
        self.mc.bcp_processor.send = MagicMock()
        self.mc.bcp_processor.enabled = True

        # Test playlist_player
        self.advance_time()
        self.mc.events.post('play_attract_music')
        self.advance_real_time(1)

        self.mc.bcp_processor.send.assert_has_calls([call('trigger', name='attract_music_played'),
                                                     call('trigger', name='attract_music_sound_changed'),
                                                     call('trigger', sound_instance=ANY, name='drumbeat_7_played')])

        status = track_playlist.get_status()
        self.assertEqual("playing", status[0]['status'])
        self.assertEqual(self.mc.sounds["drumbeat_7"].id, status[0]['sound_id'])
        self.assertEqual("idle", status[1]['status'])
        self.advance_real_time(2)

        self.mc.bcp_processor.send.reset_mock()
        self.mc.events.post('advance_playlist')
        self.advance_real_time(0.25)

        self.mc.bcp_processor.send.assert_has_calls([call('trigger', name='attract_music_sound_changed'),
                                                     call('trigger', sound_instance=ANY,
                                                          name='rainbow_disco_bears_played')])

        status = track_playlist.get_status()
        self.assertEqual("stopping", status[0]['status'])
        self.assertEqual(self.mc.sounds["drumbeat_7"].id, status[0]['sound_id'])
        self.assertEqual("playing", status[1]['status'])
        self.assertEqual(self.mc.sounds["rainbow_disco_bears"].id, status[1]['sound_id'])

        self.mc.bcp_processor.send.reset_mock()
        self.advance_real_time(2)

        self.mc.bcp_processor.send.assert_has_calls([call('trigger', sound_instance=ANY,
                                                          name='drumbeat_7_stopped'),
                                                     call('trigger', sound_instance=ANY,
                                                          name='playlist_playlist_sound_stopped'),
                                                     call('trigger', name='attract_music_sound_stopped')])

        status = track_playlist.get_status()
        self.assertEqual("idle", status[0]['status'])
        self.assertEqual("playing", status[1]['status'])
        self.assertEqual(self.mc.sounds["rainbow_disco_bears"].id, status[1]['sound_id'])

        self.mc.bcp_processor.send.reset_mock()
        self.advance_real_time(15)

        self.mc.bcp_processor.send.assert_has_calls([call('trigger', sound_instance=ANY,
                                                          name='playlist_playlist_sound_about_to_finish'),
                                                     call('trigger', name='attract_music_sound_changed'),
                                                     call('trigger', sound_instance=ANY,
                                                          name='dirty_grinding_beat_loop_played'),
                                                     call('trigger', sound_instance=ANY,
                                                          name='rainbow_disco_bears_stopped'),
                                                     call('trigger', sound_instance=ANY,
                                                          name='playlist_playlist_sound_stopped'),
                                                     call('trigger', name='attract_music_sound_stopped')])

        status = track_playlist.get_status()
        self.assertEqual("playing", status[0]['status'])
        self.assertEqual(self.mc.sounds["dirty_grinding_beat_loop"].id, status[0]['sound_id'])

        self.advance_real_time(2)
        self.mc.bcp_processor.send.reset_mock()

        self.mc.events.post('advance_playlist')
        self.advance_real_time(0.25)

        status = track_playlist.get_status()
        self.assertEqual("stopping", status[0]['status'])
        self.assertEqual(self.mc.sounds["dirty_grinding_beat_loop"].id, status[0]['sound_id'])
        self.assertEqual("playing", status[1]['status'])
        self.assertEqual(self.mc.sounds["hippie_ahead"].id, status[1]['sound_id'])

        self.advance_real_time(2)

        self.mc.bcp_processor.send.assert_has_calls([call('trigger', name='attract_music_sound_changed'),
                                                     call('trigger', sound_instance=ANY,
                                                          name='hippie_ahead_played'),
                                                     call('trigger', sound_instance=ANY,
                                                          name='dirty_grinding_beat_loop_stopped'),
                                                     call('trigger', sound_instance=ANY,
                                                          name='playlist_playlist_sound_stopped'),
                                                     call('trigger', name='attract_music_sound_stopped')])

        self.mc.bcp_processor.send.reset_mock()
        self.mc.events.post('stop_playlist')
        self.advance_real_time(3)

        self.mc.bcp_processor.send.assert_has_calls([call('trigger', sound_instance=ANY,
                                                          name='hippie_ahead_stopped'),
                                                     call('trigger', sound_instance=ANY,
                                                          name='playlist_playlist_sound_stopped'),
                                                     call('trigger', name='attract_music_sound_stopped'),
                                                     call('trigger', name='attract_music_stopped')])

        status = track_playlist.get_status()
        self.assertEqual("idle", status[0]['status'])
        self.assertEqual("idle", status[1]['status'])

    def test_playlist_context(self):
        """ Tests clearing Playlist context"""

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
        self.assertEqual("playlist", track_playlist.name)

        playlist_controller = interface.get_playlist_controller("playlist")
        self.assertIsNotNone(playlist_controller)
        self.assertEqual("playlist", playlist_controller.name)

        # Start the playlist playing with a specified context name
        playlist_instance = playlist_controller.play("attract_music",
                                                     "test_playlist_context",
                                                     {
                                                         "crossfade_time": 0.5,
                                                         "crossfade_mode": "override"
                                                     })
        self.assertIsNotNone(playlist_instance)
        self.assertEqual(0.5, playlist_instance.crossfade_time)
        self.advance_real_time()

        status = track_playlist.get_status()
        self.assertEqual("playing", status[0]['status'])
        self.assertEqual(self.mc.sounds["drumbeat_7"].id, status[0]['sound_id'])

        # Call clear context for an unknown context (playlist should keep playing)
        playlist_controller.clear_context("unknown_context")
        self.advance_real_time()
        status = track_playlist.get_status()
        self.assertEqual("playing", status[0]['status'])
        self.assertEqual(self.mc.sounds["drumbeat_7"].id, status[0]['sound_id'])

        # Call clear context using the context we started it playing (playlist should stop)
        playlist_controller.clear_context("test_playlist_context")
        self.advance_real_time()
        status = track_playlist.get_status()
        self.assertEqual("stopping", status[0]['status'])
        self.assertEqual(self.mc.sounds["drumbeat_7"].id, status[0]['sound_id'])

        # Allow time for playlist to fully stop
        self.advance_real_time(0.5)
        status = track_playlist.get_status()
        self.assertEqual("idle", status[0]['status'])
        self.assertEqual("idle", status[1]['status'])

        # Start the playlist playing again
        playlist_instance = playlist_controller.play("attract_music",
                                                     "ignore",
                                                     {
                                                         "crossfade_time": 0.5,
                                                         "crossfade_mode": "override"
                                                     })
        self.assertIsNotNone(playlist_instance)
        self.assertEqual(0.5, playlist_instance.crossfade_time)
        self.advance_real_time()

        status = track_playlist.get_status()
        self.assertEqual("playing", status[0]['status'])
        self.assertEqual(self.mc.sounds["drumbeat_7"].id, status[0]['sound_id'])

        # Start second playlist
        other_playlist_instance = playlist_controller.play("other_playlist",
                                                           "ignore",
                                                           {
                                                               "crossfade_time": 0.5,
                                                               "crossfade_mode": "override"
                                                           })
        self.assertIsNotNone(other_playlist_instance)
        self.assertEqual(0.5, other_playlist_instance.crossfade_time)
        self.advance_real_time()

        status = track_playlist.get_status()
        self.assertEqual("stopping", status[0]['status'])
        self.assertEqual(self.mc.sounds["drumbeat_7"].id, status[0]['sound_id'])
        self.assertEqual("playing", status[1]['status'])
        self.assertEqual(self.mc.sounds["hippie_ahead"].id, status[1]['sound_id'])

        # Start third playlist with a specific context (will be pending while other two playlists
        # are fading)
        third_playlist_instance = playlist_controller.play("third_playlist",
                                                           "test_pending_context",
                                                           {
                                                               "crossfade_time": 0.5,
                                                               "crossfade_mode": "override"
                                                           })
        self.assertIsNone(third_playlist_instance)
        self.assertTrue(playlist_controller.has_pending_request)
        self.advance_real_time()

        status = track_playlist.get_status()
        self.assertEqual("stopping", status[0]['status'])
        self.assertEqual(self.mc.sounds["drumbeat_7"].id, status[0]['sound_id'])
        self.assertEqual("playing", status[1]['status'])
        self.assertEqual(self.mc.sounds["hippie_ahead"].id, status[1]['sound_id'])

        # Call clear context using the context for the pending request (pending request should be cleared)
        playlist_controller.clear_context("test_pending_context")
        self.assertFalse(playlist_controller.has_pending_request)
        self.advance_real_time()

        status = track_playlist.get_status()
        self.assertEqual("stopping", status[0]['status'])
        self.assertEqual(self.mc.sounds["drumbeat_7"].id, status[0]['sound_id'])
        self.assertEqual("playing", status[1]['status'])
        self.assertEqual(self.mc.sounds["hippie_ahead"].id, status[1]['sound_id'])
