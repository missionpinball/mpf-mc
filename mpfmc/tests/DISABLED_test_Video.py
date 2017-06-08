from mpfmc.tests.MpfMcTestCase import MpfMcTestCase
from mpfmc.widgets.video import VideoWidget


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

        video_widget = self.mc.targets['default'].current_slide.widgets[0]
        text = self.mc.targets['default'].current_slide.widgets[2]

        self.assertEqual(video_widget.state, 'play')
        self.assertTrue(video_widget.video.loaded)

        # removed since this is a race condition, pos = -1 if the video hasn't
        # actually started playing yet.
        # self.assertAlmostEqual(video_widget.position, 0.0, delta=.3)

        self.assertAlmostEqual(video_widget.video.duration, 7.96, delta=.5)
        self.assertEqual(video_widget.video.volume, 1.0)

        text.text = 'PLAY'
        self.advance_time(1)

        # now that 1 sec has passed, make sure the video is advancing
        self.assertGreater(video_widget.position, 0)

        # also check the size. The size isn't set until the video actually
        # starts playing, which is why we don't check it until now.
        self.assertEqual(video_widget.size, [100, 70])

        video_widget.pause()
        text.text = 'PAUSE'
        self.advance_time(.1)

        self.assertEqual('paused', video_widget.video.state)
        pos = video_widget.video.position
        self.advance_time(.5)

        # make sure it's really stopped
        self.assertEqual(pos, video_widget.video.position)

        # now start it again
        video_widget.play()
        text.text = 'PLAY'
        self.advance_time(1)

        self.assertEqual('playing', video_widget.video.state)
        self.assertGreater(video_widget.video.position, pos)

        # stop it, should go back to the beginning
        video_widget.stop()
        text.text = 'STOP'
        self.advance_time(1)
        self.assertEqual(0.0, video_widget.video.position)

        video_widget.play()
        text.text = 'PLAY FROM BEGINNING'
        self.advance_time(1)
        self.assertAlmostEqual(video_widget.video.position, 1.0, delta=.5)

        # jump to the 50% point
        video_widget.seek(.5)
        text.text = 'SEEK TO 50%'
        self.advance_time(.1)
        self.assertAlmostEqual(video_widget.video.position, 4.0, delta=.5)

        # test the volume
        video_widget.set_volume(.5)
        text.text = 'VOLUME 50% (though this vid has no audible sound)'
        self.assertEqual(.5, video_widget.video.volume)

        video_widget.set_volume(1)
        text.text = 'VOLUME 100% (though this vid has no audible sound)'
        self.assertEqual(1.0, video_widget.video.volume)

        video_widget.set_position(.5)
        text.text = 'SET POSITION TO 0.5s'
        self.advance_time(.1)
        self.assertAlmostEqual(video_widget.video.position, 0.6, delta=.5)

        # jump to the 90% point
        video_widget.seek(.9)
        video_widget.play()
        video_widget.video.set_end_behavior('stop')
        text.text = 'JUMP TO 90%, STOP AT END'
        self.advance_time(2)
        self.assertEqual(video_widget.video.position, 0)

        # jump to the 90% point
        video_widget.seek(.9)
        video_widget.play()
        video_widget.video.set_end_behavior('pause')
        text.text = 'JUMP TO 90%, PAUSE AT END'
        self.advance_time(2)
        self.assertAlmostEqual(video_widget.video.position, 7.9, delta=.5)

        # jump to the 90% point
        video_widget.seek(.9)
        video_widget.play()
        video_widget.video.set_end_behavior('loop')
        text.text = 'JUMP TO 90%, LOOP AT END'
        self.advance_time(2)
        self.assertAlmostEqual(video_widget.video.position, 1, delta=.5)

    def test_control_events(self):
        self.mc.events.post('show_slide2')
        self.advance_real_time(1)

        video_widget = self.mc.targets['default'].current_slide.widgets[0].widget
        text = self.mc.targets['default'].current_slide.widgets[2].widget
        text.text = "PLAY"

        self.assertEqual('playing', video_widget.video.state)
        self.assertGreater(video_widget.video.position, 0)

        self.mc.events.post('stop1')
        text.text = 'STOP'
        self.advance_real_time()
        self.assertEqual(0.0, video_widget.video.position)

        self.mc.events.post('play1')
        text.text = 'PLAY'
        self.advance_real_time(1)
        self.assertGreater(video_widget.video.position, 0)

        self.mc.events.post('pause1')
        text.text = 'PAUSE'
        self.advance_real_time()
        pos = video_widget.video.position
        self.advance_real_time()
        self.assertEqual(video_widget.video.position, pos)

        self.mc.events.post('seek1')
        text.text = 'SEEK'
        self.advance_real_time()
        self.assertAlmostEqual(video_widget.video.position, 3.5, delta=.5)

        self.mc.events.post('mute')
        text.text = 'VOLUME (MUTE)'
        self.advance_real_time()
        self.assertEqual(0, video_widget.video.volume)

        self.mc.events.post('position1')
        text.text = "JUMP TO POSITION 4s"
        self.advance_real_time()
        self.assertAlmostEqual(video_widget.video.position, 4.0, delta=.1)

        # remove widget and verify control events are removed
        self.mc.targets['default'].remove_slide('video_test2')
        self.advance_time()
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'default_blank')

        self.assertFalse(self.mc.events.does_event_exist('play1'))
        self.assertFalse(self.mc.events.does_event_exist('stop1'))
        self.assertFalse(self.mc.events.does_event_exist('pause1'))
        self.assertFalse(self.mc.events.does_event_exist('seek1'))
        self.assertFalse(self.mc.events.does_event_exist('mute'))
        self.assertFalse(self.mc.events.does_event_exist('position1'))

    def test_video_settings(self):
        self.mc.events.post('show_slide7')
        self.advance_time(1)
        video_widget = self.mc.targets['default'].current_slide.widgets[0]

        # make sure it's playing
        self.assertEqual('playing', video_widget.video.state)
        self.assertEqual(0.2, video_widget.video.volume)
        last_pos = video_widget.video.position
        self.advance_time(1)

        # make sure the current position is about 1 sec later than last
        self.assertAlmostEqual(1, video_widget.video.position - last_pos, delta=.2)

        # jump to 90%
        self.mc.events.post('seek1')
        self.advance_time()
        self.assertGreater(video_widget.video.position, 7)

        # wait for the video to end and make sure it loops
        self.advance_time(2)
        last_pos = video_widget.video.position
        self.advance_time(1)

        # should still be playing, make sure the current position is about 1
        # sec later than last
        self.assertAlmostEqual(1, video_widget.video.position - last_pos, delta=.2)

        # stop and reset the video since it's the same asset used in the next
        # slide
        video_widget.stop()
        self.advance_time(.1)

        self.mc.events.post('show_slide8')
        self.advance_time(1)
        video_widget = self.mc.targets['default'].current_slide.widgets[0]

        self.assertEqual('', video_widget.video.state)
        # stopped state is empty string

        self.assertEqual(video_widget.video.position, 0.0)
        self.advance_time()
        self.assertEqual(video_widget.video.position, 0.0)
        self.assertEqual(0.8, video_widget.video.volume)

        self.mc.events.post('play1')
        self.advance_time()

        # wait for the video to end and make sure it stops
        self.mc.events.post('seek1')
        self.advance_time(2)
        self.assertEqual(video_widget.video.position, 0.0)

        self.advance_time(1)
        self.assertEqual(video_widget.video.position, 0.0)

    def test_pre_show_slide(self):
        self.mc.events.post('show_slide3')
        self.advance_time()

    def test_show_slide(self):
        self.mc.events.post('show_slide4')
        self.advance_time()

    def test_pre_slide_leave(self):
        self.mc.events.post('show_slide5')
        self.advance_time()

    def test_slide_leave(self):
        self.mc.events.post('show_slide6')
        self.advance_time()

    def test_video_stops_on_slide_removal(self):
        self.mc.events.post('show_slide9')
        self.advance_time()
        self.assertEqual(self.mc.targets['default'].current_slide.name, 'video_test9')

        # start mode1, its slide with video should come up
        self.mc.modes['mode1'].start()
        self.advance_time()

        self.mc.events.post('mode_mode1_started')
        self.advance_time(2)
        self.assertEqual(self.mc.targets['default'].current_slide.name, 'mode1_slide1')

        video_widget = self.mc.targets['default'].current_slide.widgets[0]
        self.assertTrue(isinstance(video_widget, VideoWidget))
        self.assertEqual(video_widget.state, 'play')

        # stop mode 1, should unload the slide
        self.mc.modes['mode1'].stop()
        self.advance_time()
        self.assertEqual(self.mc.targets['default'].current_slide.name, 'video_test9')

        self.assertEqual(video_widget.state, 'stop')
