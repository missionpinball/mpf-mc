from tests.MpfMcTestCase import MpfMcTestCase
from mock import MagicMock
import time
from mc.core.sound import SoundController

pinaudio_imported = True
try:
    import pinaudio
except ImportError:
    pinaudio_imported = False


class TestSoundController(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/sound_controller'

    def get_config_file(self):
        return 'test_sound_controller.yaml'

    def get_sound_file_path(self):
        return 'tests/machine_files/sound_controller/sounds'

    def test_pinaudio_libray(self):
        """ Tests the basic PinAudio libary functions independent of the media controller """
        self.assertTrue(pinaudio_imported, "Could not import the PinAudio library")
        if not pinaudio_imported:
            return

        # Initialize the audio output using the PinAudio library
        audio_output = pinaudio.get_audio_output()
        self.assertIsNotNone(audio_output)

        # Attempt to load several test sound files

        # Load the default sound format (WAV)
        wav_sound_num = audio_output.load_sample(self.get_sound_file_path() + '/Test.wav')
        self.assertGreater(wav_sound_num, 0, "Could not load the specified sound file")

        # Load OGG format (if the library supports it)
        ogg_sound_num = audio_output.load_sample(self.get_sound_file_path() + '/Test.ogg')
        if audio_output.supports_ogg:
            self.assertGreater(ogg_sound_num, 0, "Could not load the specified sound file")
        else:
            self.assertEqual(ogg_sound_num, 0,
                             "File loaded event though OGG files are reported by PinAudio to not be supported")

        # Load FLAC format (if the library supports it)
        flac_sound_num = audio_output.load_sample(self.get_sound_file_path() + '/Test.flac')
        if audio_output.supports_flac:
            self.assertGreater(flac_sound_num, 0, "Could not load the specified sound file")
        else:
            self.assertEqual(sound_num, 0,
                             "File loaded event though FLAC files are reported by PinAudio to not be supported")

        # Add a mixer channel (with limit of 2 simultaneous sounds)
        mixer_channel = audio_output.add_mixer_channel(2)
        self.assertGreaterEqual(mixer_channel, 0)

        # Get the mixer channel status
        status = audio_output.get_mixer_channel_status(mixer_channel)
        self.assertIsNotNone(status)
        self.assertEqual(len(status), 2)
        self.assertEqual(status[0]['status'], 0)
        self.assertEqual(status[1]['status'], 0)

        # Try playing a sound before enabling the mixer channel
        result = audio_output.play_sample_on_mixer_channel(wav_sound_num, mixer_channel, 1.0)
        self.assertFalse(result)

        # Now enable the mixer channel and try playing the sound again
        audio_output.enable_mixer_channel(mixer_channel)
        result = audio_output.play_sample_on_mixer_channel(wav_sound_num, mixer_channel, 1.0)
        self.assertTrue(result)
        status = audio_output.get_mixer_channel_status(mixer_channel)
        self.assertIsNotNone(status)
        self.assertIn(status[0]['status'], [1, 2])  # Sample player should either be pending or playing
        self.assertEqual(status[0]['sample_number'], wav_sound_num)

        # Test PinAudio event callback functions (sound_start, sound_stop)
        start_sound_fn = MagicMock()
        audio_output.set_sound_start_callback(start_sound_fn)
        time.sleep(0.5)
        audio_output.process_event_callbacks()
        start_sound_fn.assert_called_with(channel=0, player=0, sample_number=wav_sound_num)
        stop_sound_fn = MagicMock()
        audio_output.set_sound_stop_callback(stop_sound_fn)
        time.sleep(1.0)
        audio_output.process_event_callbacks()
        stop_sound_fn.assert_called_with(channel=0, player=0, sample_number=wav_sound_num)

