import logging

from mpfmc.tests.MpfMcTestCase import MpfMcTestCase
from unittest.mock import MagicMock, call
from mpfmc.widgets.video import VideoWidget

try:
    from mpfmc.core.audio import SoundSystem
    from mpfmc.assets.sound import SoundStealingMethod
except ImportError:
    SoundSystem = None
    SoundStealingMethod = None
    logging.warning("mpfmc.core.audio library could not be loaded. Audio "
                    "features will not be available")


class TestAudioGStreamer(MpfMcTestCase):
    """
    Tests the GStreamer audio features in the media controller.  The core audio library is a
    custom extension library written in Cython that interfaces with the SDL2 and
    SDL_Mixer libraries.
    """
    def get_machine_path(self):
        return 'tests/machine_files/audio'

    def get_config_file(self):
        return 'test_audio_gstreamer.yaml'

    def test_loading_while_playing_video(self):
        """ Tests loading a sound file while playing a video (both using gstreamer) """

        if SoundSystem is None or self.mc.sound_system is None:
            log = logging.getLogger('TestAudio')
            log.warning("Sound system is not enabled - skipping audio tests")
            self.skipTest("Sound system is not enabled")

        self.assertIsNotNone(self.mc.sound_system)
        interface = self.mc.sound_system.audio_interface
        self.assertIsNotNone(interface)

        # Mock BCP send method
        self.mc.bcp_processor.send = MagicMock()
        self.mc.bcp_processor.enabled = True

        # Make sure the low quality test video exists
        self.assertIn('mpf_video_small_test', self.mc.videos)

        self.mc.events.post('show_slide1')
        self.advance_time()

        video_widget = self.mc.targets['default'].current_slide.children[0].children[0]

        self.assertEqual(video_widget.state, 'play')
        self.assertTrue(video_widget.video.loaded)

        self.mc.events.post('play_sound_sfx_028')
        self.advance_time(1)
        self.mc.events.post('play_city_loop')

        self.advance_time(1)

        self.mc.events.post('play_sound_text')
        self.advance_time(0.35)
        self.mc.events.post('play_sound_text')
        self.advance_time(4)

        self.mc.bcp_processor.send.assert_any_call('trigger', name='text_sound_played')



