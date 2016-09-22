from mpfmc.tests.MpfIntegrationTestCase import MpfIntegrationTestCase
from mpfmc.tests.MpfSlideTestCase import MpfSlideTestCase


class TestWidgetsAndSlides(MpfIntegrationTestCase, MpfSlideTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'integration/machine_files/widgets_and_slides/'

    def test_widget_on_slide_of_another_mode(self):
        self.post_event("start_mode1")
        self.advance_time_and_run()
        self.post_event("show_widget_mode1_on_slide_mode2")
        self.advance_time_and_run()

        self.assertSlideNotActive("slide_mode2")

        self.post_event("start_mode2")
        self.advance_time_and_run()
        self.post_event("show_slide_mode2")
        self.advance_time_and_run()

        self.assertSlideOnTop("slide_mode2")
        self.assertTextInSlide("Widget Mode 1", "slide_mode2")

    def test_slide_on_target_of_another_mode(self):
        self.post_event("start_mode1")
        self.advance_time_and_run()
        self.post_event("play_slide_mode1_on_frame_mode2")
        self.advance_time_and_run()

        self.assertTextNotOnTopSlide("Slide Mode 1")

        self.post_event("start_mode2")
        self.advance_time_and_run()
        self.post_event("show_slide_mode2_frame")
        self.advance_time_and_run()

        self.assertSlideOnTop("slide_mode2_frame")
        self.assertTextInSlide("Slide Mode 1", "slide_mode2_frame")
        self.assertTextOnTopSlide("Slide Mode 1")

        # remove slide frame
        self.post_event("remove_slide_mode2_frame")
        self.advance_time_and_run()

        self.assertTextNotOnTopSlide("Slide Mode 1")

        # add again
        self.post_event("show_slide_mode2_frame")
        self.advance_time_and_run()

        # text should be there again
        self.assertTextOnTopSlide("Slide Mode 1")

        self.post_event("remove_slide_mode1_on_frame_mode2")
        self.advance_time_and_run()

        # text should not be there
        self.assertTextNotOnTopSlide("Slide Mode 1")

        # add text
        self.post_event("play_slide_mode1_on_frame_mode2")
        self.advance_time_and_run()

        # text should be there again
        self.assertTextOnTopSlide("Slide Mode 1")

        # remove slide frame
        self.post_event("remove_slide_mode2_frame")
        self.advance_time_and_run()

        # add again
        self.post_event("show_slide_mode2_frame")
        self.advance_time_and_run()

        # text should be there again
        self.assertTextOnTopSlide("Slide Mode 1")

        # remove slide frame
        self.post_event("remove_slide_mode2_frame")
        self.advance_time_and_run()

        self.post_event("remove_slide_mode1_on_frame_mode2")
        self.advance_time_and_run()

        # add again
        self.post_event("show_slide_mode2_frame")
        self.advance_time_and_run()

        # text should not be there
        self.assertTextNotOnTopSlide("Slide Mode 1")

    def test_moving_slide_frame(self):
        self.post_event("start_mode3")
        self.advance_time_and_run()
        self.assertModeRunning("mode3")

        self.post_event("show_top_slide")
        self.advance_time_and_run()
        self.post_event("show_content_slide")
        self.advance_time_and_run()

        self.assertTextOnTopSlide("ASD")
        self.assertTextOnTopSlide("ASD2")

        self.assertAlmostEqual(-134.0, self.mc.active_slides['top_slide'].children[0].children[0].y)

        self.post_event("move_out")
        self.advance_time_and_run()
        self.assertAlmostEqual(-100.0, self.mc.active_slides['top_slide'].children[0].children[0].y)
        self.post_event("move_back")
        self.advance_time_and_run()

        self.assertAlmostEqual(-134.0, self.mc.active_slides['top_slide'].children[0].children[0].y)


