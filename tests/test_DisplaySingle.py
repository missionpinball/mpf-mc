from copy import copy

from mc.uix.display import Display
from mc.uix.slide import Slide
from mc.uix.slide_frame import SlideFrame
from .MpfMcTestCase import MpfMcTestCase


class TestDisplaySingle(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/display'

    def get_config_file(self):
        return 'test_display_single.yaml'

    def test_mc_display(self):
        # Make sure a single display is loaded properly:

        self.assertIn('window', self.mc.displays)
        self.assertTrue(isinstance(self.mc.displays['window'], Display))
        self.assertEqual(self.mc.displays['window'].size, [401, 301])
        self.assertEqual(self.mc.targets['default'], self.mc.targets[
            'window'])

        # walk the display's widget tree and make sure everything is right
        widget_hierarchy = ['display', 'slide_frame']
        for widget, name in zip(self.mc.displays['window'].walk(),
                                widget_hierarchy):
            getattr(self, 'check_{}'.format(name))(widget=widget)

    def check_display(self, widget):
        self.assertTrue(isinstance(widget, Display))

    def check_slide_frame(self, widget):
        self.assertTrue(isinstance(widget, SlideFrame))
        self.assertEqual(widget.size, [401, 301])

    def test_current_slide_properties(self):
        slide1 = Slide(mc=self.mc, name='slide1', config={})

        # test display properties
        self.assertEqual(self.mc.displays['window'].current_slide, slide1)
        self.assertEqual(self.mc.displays['window'].current_slide_name,
                         'slide1')

        # test display slide_frame properties
        self.assertEqual(self.mc.displays['window'].slide_frame.current_slide,
                         slide1)
        self.assertEqual(self.mc.displays['window'].slide_frame.current_slide_name,
                         'slide1')

        # test slide_frame properties
        self.assertEqual(
                self.mc.targets['window'].current_slide,
                slide1)
        self.assertEqual(
                self.mc.targets['window'].current_slide_name,
                'slide1')

        # test target properties
        self.assertEqual(
                self.mc.targets['window'].current_slide,
                slide1)
        self.assertEqual(
                self.mc.targets['window'].current_slide_name,
                'slide1')

        # make sure adding a slide at the same priority replaces the current
        # one.
        slide2 = Slide(mc=self.mc, name='slide2', config={})
        self.assertEqual(self.mc.targets['window'].current_slide, slide2)
        self.assertEqual(self.mc.targets['window'].current_slide_name,
                         'slide2')
        self.assertEqual(self.mc.displays['window'].current_slide_name,
                         'slide2')
        self.assertEqual(self.mc.displays['window'].current_slide, slide2)

        # test property setters for slide frames
        self.mc.targets['window'].current_slide = 'slide1'
        self.assertEqual(self.mc.targets['window'].current_slide, slide1)

        self.mc.targets['window'].current_slide_name = 'slide2'
        self.assertEqual(self.mc.targets['window'].current_slide, slide2)

        self.mc.targets['window'].current_slide = slide1
        self.assertEqual(self.mc.targets['window'].current_slide, slide1)

        # test property setters for displays
        self.mc.displays['window'].current_slide = slide2
        self.assertEqual(self.mc.targets['window'].current_slide, slide2)

        self.mc.displays['window'].current_slide = 'slide1'
        self.assertEqual(self.mc.targets['window'].current_slide, slide1)

        self.mc.displays['window'].current_slide_name = 'slide2'
        self.assertEqual(self.mc.targets['window'].current_slide, slide2)

    def test_priorities(self):
        slide1 = Slide(mc=self.mc, name='slide1', config={}, priority=100)
        self.assertEqual(self.mc.targets['window'].current_slide, slide1)

        slide2 = Slide(mc=self.mc, name='slide2', config={}, priority=0)
        self.assertEqual(self.mc.targets['window'].current_slide, slide1)

        slide3 = Slide(mc=self.mc, name='slide3', config={}, priority=200)
        self.assertEqual(self.mc.targets['window'].current_slide, slide3)

        slide4 = copy(slide3)
        # since slides add themselves on creation, we need to not run that
        # again
        slide4.priority = 199
        self.assertLess(slide4.priority,
                        self.mc.targets['window'].current_slide.priority)

        self.mc.targets['window'].add_widget(slide=slide4)

        # slide should not show
        self.assertEqual(self.mc.targets['window'].current_slide, slide3)

        # test force
        slide5 = copy(slide3)
        slide5.priority = 199
        slide5.name = 'slide5'
        self.assertLess(slide5.priority,
                        self.mc.targets['window'].current_slide.priority)

        self.mc.targets['window'].add_widget(slide=slide5,
                                                          force=True)

        # slide should show
        self.assertEqual(self.mc.targets['window'].current_slide, slide5)

        # test not showing
        slide6 = copy(slide3)
        slide6.priority = 300
        slide5.name = 'slide6'
        self.assertGreater(slide6.priority,
                           self.mc.targets['window'].current_slide.priority)

        self.mc.targets['window'].add_widget(slide=slide6,
                                                          show=False)

        # slide should not show
        self.assertEqual(self.mc.targets['window'].current_slide, slide5)
