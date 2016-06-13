from copy import copy

from kivy.uix.stencilview import StencilView

from mpfmc.uix.display import Display
from mpfmc.uix.slide import Slide
from mpfmc.uix.slide_frame import SlideFrame, SlideFrameParent
from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


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
        widget_hierarchy = ['display', 'slide_frame_parent', 'stencil', 'slide_frame']
        for widget, name in zip(self.mc.displays['window'].walk(),
                                widget_hierarchy):
            getattr(self, 'check_{}'.format(name))(widget=widget)

    def check_display(self, widget):
        self.assertTrue(isinstance(widget, Display))

    def check_stencil(self, widget):
        self.assertTrue(isinstance(widget, StencilView))

    def check_slide_frame(self, widget):
        self.assertTrue(isinstance(widget, SlideFrame))
        self.assertEqual(widget.size, [401, 301])

    def check_slide_frame_parent(self, widget):
        self.assertTrue(isinstance(widget, SlideFrameParent))

    def test_current_slide_properties(self):
        slide1 = Slide(mc=self.mc, name='slide1')

        # test display properties
        self.assertEqual(self.mc.displays['window'].current_slide, slide1)
        self.assertEqual(self.mc.displays['window'].current_slide_name,
                         'slide1')

        # test display slide_frame properties
        self.assertEqual(self.mc.displays['window'].slide_frame.current_slide,
                         slide1)
        self.assertEqual(
            self.mc.displays['window'].slide_frame.current_slide_name,
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

        # make sure showing a slide at the same priority replaces the current
        # one.
        slide2 = Slide(mc=self.mc, name='slide2')
        self.mc.targets['window'].show_slide('slide2')

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

         # we need to wait a tick to remove the slide we just added
        self.advance_time()

        # now remove the current slide and make sure slide1 comes back
        self.mc.targets['window'].remove_slide(slide2)
        self.assertEqual(self.mc.targets['window'].current_slide, slide1)

        # add another slide so we have 2
        slide3 = Slide(mc=self.mc, name='slide3', config={})
        self.assertEqual(len(self.mc.targets['window'].slides), 2)

        # also test removing by name
        self.mc.targets['window'].remove_slide('slide1')
        self.assertEqual(self.mc.targets['window'].current_slide, slide3)

    def test_priorities(self):
        # show slide 1, p100
        slide1 = Slide(mc=self.mc, name='slide1', priority=100)
        self.mc.targets['window'].show_slide('slide1')
        self.assertEqual(self.mc.targets['window'].current_slide, slide1)

        # show slide 2, p0, it should not show
        slide2 = Slide(mc=self.mc, name='slide2', priority=0)
        self.mc.targets['window'].show_slide('slide2')
        self.assertEqual(self.mc.targets['window'].current_slide, slide1)

        # show slide 3, p200, it should show
        slide3 = Slide(mc=self.mc, name='slide3', config={}, priority=200)
        self.mc.targets['window'].show_slide('slide3')
        self.assertEqual(self.mc.targets['window'].current_slide, slide3)

        # show slide 4, p199, it should not show
        slide4 = Slide(mc=self.mc, name='slide4', config={}, priority=199)
        self.mc.targets['window'].show_slide('slide4')
        self.assertLess(slide4.priority,
                        self.mc.targets['window'].current_slide.priority)

        # confirm that slide 3 is still current
        self.assertEqual(self.mc.targets['window'].current_slide, slide3)

        # force slide 4 to show
        self.assertLess(slide4.priority,
                        self.mc.targets['window'].current_slide.priority)
        self.mc.targets['window'].show_slide('slide4', force=True)

        # slide should show
        self.assertEqual(self.mc.targets['window'].current_slide_name,
                         'slide4')

