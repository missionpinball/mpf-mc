
from tests.MpfMcTestCase import MpfMcTestCase


class TestVideo(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/video'

    def get_config_file(self):
        return 'test_video.yaml'

    def test_video(self):

        self.assertIn('mpf_video_small_test', self.mc.videos)

        self.mc.events.post('show_slide1')
        self.advance_time(2)

        video_widget = self.mc.targets['default'].current_slide.children[0]

        self.assertEqual(video_widget.state, 'play')
        self.assertAlmostEqual(video_widget.duration, 7.9, delta=.1)
        self.assertEqual(video_widget.volume, 1.0)
        self.assertEqual(video_widget.size, [398, 248])

        self.advance_time(1)
