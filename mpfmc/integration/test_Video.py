from mpfmc.tests.MpfIntegrationTestCase import MpfIntegrationTestCase


class TestVideo(MpfIntegrationTestCase):

    def get_machine_path(self):
        return 'integration/machine_files/video'

    def get_config_file(self):
        return 'config.yaml'

    def test_video_stops_on_slide_removal(self):
        # start mode1, its slide with video should come up
        self.post_event("start_mode1")
        self.advance_time_and_run()

        self.assertEqual(self.mc.targets['default'].current_slide.name, 'mode1_slide1')
        video_widget = self.mc.targets['default'].current_slide.widgets[0].widget
        self.assertEqual(video_widget.state, 'play')
        self.assertTrue(video_widget.video.loaded)

        # stop mode 1, should unload the slide
        self.post_event("stop_mode1")
        self.advance_time_and_run()
        self.assertEqual(self.mc.targets['default'].current_slide.name, 'default_blank')
        # check that the video is unloaded (because the widget will not be stopped)
        self.assertFalse(video_widget.video.loaded)

    def test_video_control_events_from_mpf(self):
        # start mode1, its slide with video should come up
        self.post_event("start_mode1")
        self.advance_time_and_run()

        self.assertEqual(self.mc.targets['default'].current_slide.name, 'mode1_slide1')
        video_widget = self.mc.targets['default'].current_slide.widgets[0].widget
        self.assertEqual(video_widget.state, 'play')
        self.assertTrue(video_widget.video.loaded)

        self.post_event("pause_event_from_mpf")
        self.advance_time_and_run(.1)
        self.assertEqual(video_widget.state, 'pause')

    def test_video_control_events_from_mpf_in_show(self):
        self.post_event("play_show_with_video")
        self.advance_time_and_run(.1)
        video_widget = self.mc.targets['default'].current_slide.widgets[0].widget
        self.assertEqual(video_widget.state, 'play')
        self.assertTrue(video_widget.video.loaded)

        self.post_event("pause_event_from_mpf2")
        self.advance_time_and_run(.1)
        self.assertEqual(video_widget.state, 'pause')
