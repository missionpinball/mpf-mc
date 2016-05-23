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
        text = self.mc.targets['default'].current_slide.children[0].children[2]

        self.assertEqual(video_widget.state, 'play')
        self.assertTrue(video_widget.video.loaded)

        self.assertAlmostEqual(video_widget.position, 0.0, delta=.3)

        # from the travis log:
        # --------------------------------
        # E: Unable to locate package libgstreamer1.0-dev E: Couldn't find any package by regex 'libgstreamer1.0-dev'
        # E: Unable to locate package gstreamer1.0-alsa
        # E: Couldn't find any package by regex 'gstreamer1.0-alsa'
        # E: Unable to locate package gstreamer1.0-plugins-bad
        # E: Couldn't find any package by regex 'gstreamer1.0-plugins-bad'
        # E: Unable to locate package gstreamer1.0-plugins-base
        # E: Couldn't find any package by regex 'gstreamer1.0-plugins-base'
        # E: Unable to locate package gstreamer1.0-plugins-good
        # E: Couldn't find any package by regex 'gstreamer1.0-plugins-good'
        # E: Unable to locate package gstreamer1.0-plugins-ugly
        # E: Couldn't find any package by regex 'gstreamer1.0-plugins-ugly'
        # --------------------------------

        self.assertAlmostEqual(video_widget.video.duration, 7.96, delta=.1)
        self.assertEqual(video_widget.video.volume, 1.0)

        text.text = 'PLAY'
        self.advance_time(1)

        # now that 1 sec has passed, make sure the video is advancing
        self.assertAlmostEqual(video_widget.position, 1.0, delta=.3)

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
        self.assertAlmostEqual(video_widget.video.position, 1.0, delta=.2)

        # jump to the 50% point
        video_widget.seek(.5)
        text.text = 'SEEK TO 50%'
        self.advance_time(.1)
        self.assertAlmostEqual(video_widget.video.position, 4.0, delta=.2)

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
        self.assertAlmostEqual(video_widget.video.position, 0.6, delta=.1)

        # jump to the 90% point
        video_widget.seek(.9)
        video_widget.play()
        video_widget.video.set_end_behavior('stop')
        text.text = 'JUMP TO 90%, STOP AT END'
        self.advance_time(2)
        self.assertAlmostEqual(video_widget.video.position, 7.9, delta=.1)

        # jump to the 90% point
        video_widget.seek(.9)
        video_widget.play()
        video_widget.video.set_end_behavior('pause')
        text.text = 'JUMP TO 90%, PAUSE AT END'
        self.advance_time(2)
        self.assertAlmostEqual(video_widget.video.position, 7.9, delta=.1)

        # jump to the 90% point
        video_widget.seek(.9)
        video_widget.play()
        video_widget.video.set_end_behavior('loop')
        text.text = 'JUMP TO 90%, LOOP AT END'
        self.advance_time(2)
        self.assertAlmostEqual(video_widget.video.position, 1, delta=.1)
