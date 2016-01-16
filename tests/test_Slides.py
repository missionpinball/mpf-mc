from .MpfMcTestCase import MpfMcTestCase
from mc.uix.slide import Slide


class TestSlides(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/slide'

    def get_config_file(self):
        return 'test_slides.yaml'

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
                        slide_frame=self.mc.default_display.slide_frame,
                        mode='attract',
                        priority=0)

        self.assertIs(slide.mode, self.mc.modes['attract'])

    def test_mode_by_object(self):
        slide = Slide(mc=self.mc,
                        name='slide1',
                        config=self.mc.machine_config['slides']['slide1'],
                        slide_frame=self.mc.default_display.slide_frame,
                        mode=self.mc.modes['attract'],
                        priority=0)

        self.assertIs(slide.mode, self.mc.modes['attract'])

    def test_priority_passed(self):
        slide = Slide(mc=self.mc,
                        name='slide1',
                        config=self.mc.machine_config['slides']['slide1'],
                        slide_frame=self.mc.default_display.slide_frame,
                        mode=self.mc.modes['attract'],
                        priority=123)

        self.assertEqual(slide.priority, 123)

    def test_priority_from_mode(self):
        slide = Slide(mc=self.mc,
                        name='slide1',
                        config=self.mc.machine_config['slides']['slide1'],
                        slide_frame=self.mc.default_display.slide_frame,
                        mode=self.mc.modes['attract'])

        self.assertEqual(slide.priority, self.mc.modes['attract'].priority)

    def test_no_priority_no_mode(self):
        slide = Slide(mc=self.mc,
                        name='slide1',
                        config=self.mc.machine_config['slides']['slide1'],
                        slide_frame=self.mc.default_display.slide_frame)

        self.assertIs(slide.priority, 0)

    def test_widgets_from_config(self):
        slide = Slide(mc=self.mc,
                        name='slide1',
                        config=self.mc.machine_config['slides']['slide1'],
                        slide_frame=self.mc.default_display.slide_frame,
                        mode='attract',
                        priority=0)

        widget_tree = list()
        for s in slide.walk():
            widget_tree.append(s)

        # last widget is drawn last (on top), so the order should be flipped
        self.assertEqual(widget_tree[1].text, 'text3')
        self.assertEqual(widget_tree[2].text, 'text2')
        self.assertEqual(widget_tree[3].text, 'text1')

