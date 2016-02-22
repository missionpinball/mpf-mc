
from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestVideo(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/video'

    def get_config_file(self):
        return 'test_video.yaml'

    def test_video(self):

        # Note the green bar on the bottom of this video is part of it. It is
        # VERY low quality to keep the mpf-mc package small. :)
        self.assertIn('mpf_video_small_test', self.mc.videos)

        self.mc.events.post('show_slide1')
        self.advance_time(1)

        # This works locally but not on travis. I need to figure out the right
        # library & format that can run on travis.

        # video_widget = self.mc.targets['default'].current_slide.children[0]
        #
        # self.assertEqual(video_widget.state, 'play')
        # self.assertTrue(video_widget.loaded)
        # self.assertAlmostEqual(video_widget.position, .8, delta=.3)
        # self.assertAlmostEqual(video_widget.duration, 7.79, delta=.1)
        # self.assertEqual(video_widget.volume, 1.0)
        # self.assertEqual(video_widget.size, [400, 258])
        #
        # self.advance_time(5)
