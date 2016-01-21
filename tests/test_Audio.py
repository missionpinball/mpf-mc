from tests.MpfMcTestCase import MpfMcTestCase
from mock import MagicMock
import time

import mc.core.audio.audio_interface as audio_interface


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
        audio = audio_interface.get_audio_interface()
        self.assertIsNotNone(audio)

    def test_sound_controller(self):
        pass

    # TODO: Tests to write:
    # Add track
    # Add another track with the same name
    # Add another track with the same name (but different casing)
    # Attempt to add too many tracks (more than 8)
    # Attempt to create track with max_simultaneous_sounds > 32 (the current max)
    # Attempt to create track with max_simultaneous_sounds < 0 (the current max)
    # Load sounds (wav, ogg, flac, unsupported format)
    # Play a sound
    # Play two sounds on track with max_simultaneous_sounds = 1 (test sound queue, time expiration, priority scenarios)
    # Play a sound on each track simultaneously
    # Stop all sounds on track
    # Stop all sounds on all tracks
    # Ducking
    # Configuration file tests (audio interface, tracks, sounds, sound player, sound trigger events, etc.)
    #
