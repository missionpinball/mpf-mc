from tests.MpfMcTestCase import MpfMcTestCase
from mock import MagicMock
import time

from mc.core.audio import AudioInterface, SoundController


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

    def test_audio_library(self):
        """ Tests the basic audio library functions """

        # Load the audio interface
        interface = AudioInterface.initialize()
        self.assertIsNotNone(interface)

        # Add a track
        track = interface.create_track("test", 2)
        self.assertIsNotNone(track)
        self.assertEqual(track.number, 0)
        self.assertEqual(track.volume, 1.0)
        self.assertEqual(track.name, "test")

        # Add another track with the same name (should not be allowed)
        track_duplicate = interface.create_track("test", 4)
        self.assertIsNone(track_duplicate)

        # Add another track with the same name, but different casing (should not be allowed)
        track_duplicate = interface.create_track("Test", 2)
        self.assertIsNone(track_duplicate)

        # Attempt to create track with max_simultaneous_sounds > 32 (the current max)
        track_max_sounds = interface.create_track("BIG", 33)
        self.assertIsNotNone(track_max_sounds)
        self.assertEqual(track_max_sounds.max_simultaneous_sounds, 32)
        self.assertEqual(track_max_sounds.name, "big")

        # Attempt to create track with max_simultaneous_sounds < 1 (the current max)
        track_min_sounds = interface.create_track("small", 0)
        self.assertIsNotNone(track_min_sounds)
        self.assertEqual(track_min_sounds.max_simultaneous_sounds, 1)

        # Add up to the maximum number of tracks allowed
        while interface.get_track_count() < AudioInterface.get_max_tracks():
            track = interface.create_track("track{}".format(interface.get_track_count()), 2)
            self.assertIsNotNone(track)

        # There should now be the maximum number of tracks allowed
        # Try to add another track (more than the maximum allowed)
        track = interface.create_track("toomany", 2)
        self.assertIsNone(track)

    def test_sound_controller(self):
        controller = SoundController(self.mc)
        self.assertIsNotNone(controller)

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
