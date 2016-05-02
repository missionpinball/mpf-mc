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

    def test_mode_by_name(self):

        slide = Slide(mc=self.mc,
                      name='slide1',
                      config=self.mc.slides['slide1'],
                      mode='mode1',
                      priority=0)

        self.assertIs(slide.mode, self.mc.modes['mode1'])

    def test_mode_by_object(self):
        slide = Slide(mc=self.mc,
                      name='slide1',
                      config=self.mc.slides['slide1'],
                      mode=self.mc.modes['mode1'],
                      priority=0)

        self.assertIs(slide.mode, self.mc.modes['mode1'])

    def test_priority_passed(self):
        slide = Slide(mc=self.mc,
                      name='slide1',
                      config=self.mc.slides['slide1'],
                      mode=self.mc.modes['mode1'],
                      priority=123)

        self.assertEqual(slide.priority, 123)

    def test_priority_from_mode(self):
        slide = Slide(mc=self.mc,
                      name='slide1',
                      config=self.mc.slides['slide1'],
                      mode=self.mc.modes['mode1'])

        self.assertEqual(slide.priority, self.mc.modes['mode1'].priority)

    def test_priority_merged_with_mode(self):
        self.mc.modes['mode1'].start()

        slide = Slide(mc=self.mc,
                      name='slide1',
                      config=self.mc.slides['slide1'],
                      mode=self.mc.modes['mode1'],
                      priority=123)

        self.assertEqual(self.mc.modes['mode1'].priority, 500)

        self.assertEqual(slide.priority, 123)

    def test_no_priority_no_mode(self):
        slide = Slide(mc=self.mc,
                      name='slide1',
                      config=self.mc.slides['slide1'])

        self.assertIs(slide.priority, 0)

    def test_widgets_from_config(self):
        slide = Slide(mc=self.mc,
                      name='slide1',
                      config=self.mc.slides['slide1'],
                      mode='mode1',
                      priority=0)

        widget_tree = list()
        for s in slide.children[0].walk():
            widget_tree.append(s)

        # last widget is drawn last (on top), so the order should be flipped
        self.assertEqual(widget_tree[1].text, 'SLIDE TEST 1-3')
        self.assertEqual(widget_tree[2].text, 'SLIDE TEST 1-2')
        self.assertEqual(widget_tree[3].text, 'SLIDE TEST 1-1')

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

    def test_slides_from_modes(self):
        self.assertIn('mode1_slide1', self.mc.slides)

        # set a current slide
        self.mc.targets['display1'].add_slide(name='slide1')
        self.mc.targets['display1'].show_slide('slide1')
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'slide1')

        # start a mode and add a slide from that mode
        self.mc.modes['mode1'].start()
        self.mc.targets['display1'].add_slide(name='slide2',
                                              mode=self.mc.modes['mode1'])
        self.mc.targets['display1'].show_slide('slide2')
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'slide2')
        self.assertEqual(self.mc.targets['display1'].current_slide.priority,
                         500)

        # save how many slides are active
        active_slides = len(self.mc.active_slides)

        # stop the mode and its slide should be removed
        num_slides = len(self.mc.targets['display1'].slides)
        self.mc.modes['mode1'].stop()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'slide1')
        self.assertEqual(self.mc.targets['display1'].current_slide.priority,
                         0)
        self.assertEqual(len(self.mc.targets['display1'].slides),
                         num_slides - 1)

        # Make sure we have one less active slide
        self.assertEqual(len(self.mc.active_slides), active_slides - 1)
        self.advance_time(0.01)

    def test_quick_actions(self):
        # There was a bug where immediately adding and then removing a slide
        # would crash because the kivy event loop didn't get a chance to run.

        self.mc.targets['default'].show_slide('slide1')
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')
        self.mc.targets['default'].remove_slide('slide1')
