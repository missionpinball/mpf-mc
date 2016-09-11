from mpfmc.tests.MpfIntegrationTestCase import MpfIntegrationTestCase
from mpfmc.tests.MpfSlideTestCase import MpfSlideTestCase


class TestSlidesAndWidgets(MpfIntegrationTestCase, MpfSlideTestCase):

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
