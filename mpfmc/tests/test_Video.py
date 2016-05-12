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
        self.advance_time()

        video_widget = self.mc.targets['default'].current_slide.children[0].children[0]

        self.assertEqual(video_widget.state, 'play')
        self.assertTrue(video_widget.video.loaded)

        self.assertAlmostEqual(video_widget.position, 0.0, delta=.3)
        self.assertAlmostEqual(video_widget.video.video.duration, 7.96, delta=.1)
        self.assertEqual(video_widget.video.video.volume, 1.0)

        self.advance_time(1)
        # now that 1 sec has passed, make sure the video is advancing
        self.assertAlmostEqual(video_widget.position, 1.0, delta=.3)
        # also check the size. The size isn't set until the video actually
        # starts playing, which is why we don't check it until now.
        self.assertEqual(video_widget.size, [100, 70])

        self.advance_time(4)
