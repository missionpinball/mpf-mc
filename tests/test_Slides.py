from tests.MpfMcTestCase import MpfMcTestCase
from mc.uix.slide import Slide


class TestSlides(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/slide'

    def get_config_file(self):
        return 'test_slides.yaml'

    def test_slide(self):
        slide = Slide(mc=self.mc, name='slide1', config={}, priority=100)

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
                        config=self.mc.machine_config['slides']['slide1'],
                        mode='attract',
                        priority=0)

        self.assertIs(slide.mode, self.mc.modes['attract'])

    def test_mode_by_object(self):
        slide = Slide(mc=self.mc,
                        name='slide1',
                        config=self.mc.machine_config['slides']['slide1'],
                        mode=self.mc.modes['attract'],
                        priority=0)

        self.assertIs(slide.mode, self.mc.modes['attract'])

    def test_priority_passed(self):
        slide = Slide(mc=self.mc,
                        name='slide1',
                        config=self.mc.machine_config['slides']['slide1'],
                        mode=self.mc.modes['attract'],
                        priority=123)

        self.assertEqual(slide.priority, 123)

    def test_priority_from_mode(self):
        slide = Slide(mc=self.mc,
                        name='slide1',
                        config=self.mc.machine_config['slides']['slide1'],
                        mode=self.mc.modes['attract'])

        self.assertEqual(slide.priority, self.mc.modes['attract'].priority)

    def test_priority_merged_with_mode(self):
        self.mc.modes['mode1'].start()

        slide = Slide(mc=self.mc,
                        name='slide1',
                        config=self.mc.machine_config['slides']['slide1'],
                        mode=self.mc.modes['mode1'],
                        priority=123)

        self.assertEqual(self.mc.modes['mode1'].priority, 500)

        self.assertEqual(slide.priority, 623)

    def test_no_priority_no_mode(self):
        slide = Slide(mc=self.mc,
                        name='slide1',
                        config=self.mc.machine_config['slides']['slide1'])

        self.assertIs(slide.priority, 0)

    def test_widgets_from_config(self):
        slide = Slide(mc=self.mc,
                        name='slide1',
                        config=self.mc.machine_config['slides']['slide1'],
                        mode='attract',
                        priority=0)

        widget_tree = list()
        for s in slide.walk():
            widget_tree.append(s)

        # last widget is drawn last (on top), so the order should be flipped
        self.assertEqual(widget_tree[1].text, 'SLIDE TEST - SLIDE 1 - TEXT 3')
        self.assertEqual(widget_tree[2].text, 'SLIDE TEST - SLIDE 1 - TEXT 2')
        self.assertEqual(widget_tree[3].text, 'SLIDE TEST - SLIDE 1 - TEXT 1')

    def test_slides_from_modes(self):
        self.assertIn('mode1_slide1', self.mc.slide_configs)

        # set a current slide
        self.mc.targets['display1'].add_slide(name='slide1', config={})
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'slide1')

        # start a mode and add a slide from that mode
        self.mc.modes['mode1'].start()
        self.mc.targets['display1'].add_slide(name='slide2', config={},
                                              mode=self.mc.modes['mode1'])
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'slide2')
        self.assertEqual(self.mc.targets['display1'].current_slide.priority,
                         500)

        # stop the mode and its slide should be removed
        num_slides = len(self.mc.targets['display1'].slides)
        self.mc.modes['mode1'].stop()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'slide1')
        self.assertEqual(self.mc.targets['display1'].current_slide.priority,
                         0)
        self.assertEqual(len(self.mc.targets['display1'].slides),
                         num_slides - 1)
