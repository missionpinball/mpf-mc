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

        ball = self.mc.targets['default'].children[0].children[0].children[0]
        stick_figures = self.mc.targets['default'].children[0].children[0].children[1]

        self.advance_time()

        # make sure they're playing as they should
        self.assertEqual(ball.fps, 30)
        self.assertEqual(ball.loops, 0)
        self.assertEqual(stick_figures.fps, 10)
        self.assertEqual(stick_figures.loops, 0)

        # test stopping
        stick_figures.stop()
        self.advance_time()
        stopped_frame = stick_figures.current_frame

        for x in range(10):
            self.assertEqual(stick_figures.current_frame, stopped_frame)
            self.advance_time()

        # test jumping to a new frame
        stick_figures.current_frame = 5
        self.advance_time()
        self.assertEqual(stick_figures.current_frame, 5)

        # test starting
        stick_figures.play()
        self.advance_time()
