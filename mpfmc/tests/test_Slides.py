from mpfmc.uix.slide import Slide
from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestSlides(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/slide'

    def get_config_file(self):
        return 'test_slides.yaml'

    def test_slide(self):
        slide = Slide(mc=self.mc, name='slide1', priority=100)

        self.assertEqual(slide.mc, self.mc)
        self.assertEqual(slide.name, 'slide1')
        self.assertEqual(slide.priority, 100)

    def test_mc_slide_processor(self):
        self.assertIn('slide1', self.mc.machine_config['slides'])
        self.assertIn('slide2', self.mc.machine_config['slides'])
        self.assertIn('slide3', self.mc.machine_config['slides'])
        self.assertIn('slide4', self.mc.machine_config['slides'])
        self.assertIn('slide5', self.mc.machine_config['slides'])

    def test_key_by_name(self):
        slide = Slide(mc=self.mc,
                      name='slide1',
                      config=self.mc.slides['slide1'],
                      key='mode1',
                      priority=0)

        self.assertEqual(slide.key, 'mode1')

    def test_priority_passed(self):
        slide = Slide(mc=self.mc,
                      name='slide1',
                      config=self.mc.slides['slide1'],
                      key='mode1',
                      priority=123)

        self.assertEqual(slide.priority, 123)

    def test_widgets_from_config(self):
        slide = Slide(mc=self.mc,
                      name='slide1',
                      config=self.mc.slides['slide1'],
                      key='mode1',
                      priority=0)

        widget_tree = list()
        for s in slide.children:
            widget_tree.append(s.widget)

        # Widgets are drawn in order from the end of the children list to the beginning
        # so the order should be the same order as appears in the config file.
        self.assertEqual(widget_tree[0].text, 'SLIDE TEST 1-1')
        self.assertEqual(widget_tree[1].text, 'SLIDE TEST 1-2')
        self.assertEqual(widget_tree[2].text, 'SLIDE TEST 1-3')

    def test_widgets_z_order_from_config(self):
        slide = Slide(mc=self.mc,
                      name='slide7',
                      config=self.mc.slides['slide7'],
                      key='mode1',
                      priority=0)

        widget_tree = list()
        for s in slide.children:
            widget_tree.append(s.widget)

        # Widgets are drawn in order from the end of the children list to the beginning.
        # The resulting child widget order should be the from highest z-order value in
        # the beginning of the list to lowest z-order value.  Ties should be broken by
        # the order the widgets appear in the config file.
        self.assertEqual(widget_tree[0].text, 'TEST Z-ORDER 100')
        self.assertEqual(widget_tree[1].text, 'TEST Z-ORDER 50-1')
        self.assertEqual(widget_tree[2].text, 'TEST Z-ORDER 50-2')
        self.assertEqual(widget_tree[3].text, 'TEST Z-ORDER 0')

    def test_slides_from_config(self):
        self.assertIn('slide1', self.mc.slides)
        self.assertIn('slide2', self.mc.slides)
        self.assertIn('slide3', self.mc.slides)
        self.assertIn('slide4', self.mc.slides)
        self.assertIn('transition', self.mc.slides['slide4'])
        self.assertIn('slide5', self.mc.slides)
        self.assertIn('transition', self.mc.slides['slide5'])

        # make sure it also works by attribute
        self.assertIsNotNone(self.mc.slides.slide1)

    def test_quick_actions(self):
        # There was a bug where immediately adding and then removing a slide
        # would crash because the kivy event loop didn't get a chance to run.

        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')
        self.mc.targets['default'].remove_slide('slide1')

    def test_background_color_and_opacity(self):
        slide = Slide(mc=self.mc,
                      name='slide6',
                      config=self.mc.slides['slide6'])
        self.advance_time()

        self.assertEqual(0.5, slide.canvas.opacity)

    def test_remove_non_existent_slide(self):
        self.assertFalse(self.mc.targets['default'].remove_slide('hello'))
        self.advance_time()

    def test_two_slides_in_one_tick(self):
        self.mock_event('slide_slide1_active')
        self.mock_event('slide_slide2_active')

        self.mc.targets['default'].show_slide('slide1')
        self.mc.targets['default'].show_slide('slide2')
        self.advance_time()

        self.assertEventNotCalled('slide_slide1_active')
        self.assertEventCalled('slide_slide2_active', 1)
