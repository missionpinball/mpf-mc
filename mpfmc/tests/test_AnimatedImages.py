from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestAnimatedImages(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/animated_images'

    def get_config_file(self):
        return 'test_animated_images.yaml'

    def test_animated_images_loading(self):

        self.assertEqual(self.mc.images['ball'].image._anim_index, 0)
        self.assertEqual(self.mc.images['ball'].image._anim_delay, -1)
        self.assertEqual(self.mc.images['busy-stick-figures-animated'].
                         image._anim_index, 0)
        self.assertEqual(self.mc.images['busy-stick-figures-animated'].
                         image._anim_delay, -1)
        self.assertEqual(len(self.mc.images['busy-stick-figures-animated'].
                             image.image.textures), 10)

    def test_animated_images(self):
        self.mc.events.post('slide1')
        self.advance_time()

        ball = self.mc.targets['default'].current_slide.widgets[0].widget
        stick_figures = self.mc.targets['default'].current_slide.widgets[1].widget

        self.advance_time()

        # make sure they're playing as they should
        self.assertEqual(ball.fps, 30)
        self.assertEqual(ball.loops, -1)
        self.assertEqual(stick_figures.fps, 10)
        self.assertEqual(stick_figures.loops, -1)

        # test stopping
        stick_figures.stop()
        self.advance_time()
        stopped_frame = stick_figures.current_frame

        for x in range(10):
            self.assertEqual(stick_figures.current_frame, stopped_frame)
            self.advance_time()

        # test jumping to a new frame
        stick_figures.current_frame = 5
        self.assertEqual(stick_figures.current_frame, 6)

        # test starting
        stick_figures.play()
        self.advance_time()
        self.assertTrue(self.mc.images["busy-stick-figures-animated"].image._anim_ev)
        #self.assertEqual(1, self.mc.images["busy-stick-figures-animated"].references)

        self.mc.events.post('slide2')
        self.advance_time(.2)
        self.assertTrue(self.mc.images["busy-stick-figures-animated"].image._anim_ev)
        #self.assertEqual(2, self.mc.images["busy-stick-figures-animated"].references)

        self.mc.events.post('slide1_remove')
        self.advance_time(1)
        self.assertTrue(self.mc.images["busy-stick-figures-animated"].image._anim_ev)
        #self.assertEqual(1, self.mc.images["busy-stick-figures-animated"].references)

    def test_start_frame_hold(self):
        self.mc.events.post('slide3')
        self.advance_time()
        stick_figures = self.mc.targets['default'].current_slide.widgets[0].widget
        for _ in range(4):
            self.advance_time()
            self.assertEqual(stick_figures.current_frame, 4)

    def test_skip_frames(self):
        self.mc.events.post('slide4')
        self.advance_time()
        stick_figures = self.mc.targets['default'].current_slide.widgets[0].widget
        self.advance_time()
        self.assertEqual(stick_figures.current_frame, 0)
        self.mc.events.post('advance_frames')
        self.advance_time()
        self.assertEqual(stick_figures.current_frame, 1)
        self.advance_time()
        self.assertEqual(stick_figures.current_frame, 2)
        self.advance_time()
        self.assertEqual(stick_figures.current_frame, 3)
        self.advance_time()
        self.assertEqual(stick_figures.current_frame, 9)
        self.advance_time()
        self.assertEqual(stick_figures.current_frame, 10)
        self.advance_time()
        self.assertEqual(stick_figures.current_frame, 10)
