from mpfmc.uix.slide_frame import SlideFrame, SlideFrameParent
from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestSlideFrame(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/slide_frame'

    def get_config_file(self):
        return 'test_slide_frame.yaml'

    def test_slide_frame(self):
        # put slide1 on the default displays
        self.mc.targets['default'].add_slide(name='slide1',
                                             config=self.mc.slides[
                                                 'slide1'])
        self.mc.events.post('show_slide1')
        self.advance_time()

        # make sure our slide frame is a valid target
        self.assertIn('frame1', self.mc.targets)

        # the slide frame's parent should be the first widget in slide1
        self.assertEqual(self.mc.targets['default'].current_slide.
                         children[0].children[0].name, 'frame1')

        # grab some references which are easy to follow
        default_frame = self.mc.targets['default']
        frame1_frame = self.mc.targets['frame1']
        default_frame_parent = self.mc.targets['default'].parent.parent
        frame1_frame_parent = self.mc.targets['frame1'].parent.parent

        # make sure they're right. :)
        self.assertEqual(default_frame.name, 'default')
        self.assertEqual(frame1_frame.name, 'frame1')
        self.assertEqual(default_frame_parent.name, 'default')
        self.assertEqual(frame1_frame_parent.name, 'frame1')
        self.assertTrue(isinstance(default_frame, SlideFrame))
        self.assertTrue(isinstance(frame1_frame, SlideFrame))
        self.assertTrue(isinstance(default_frame_parent, SlideFrameParent))
        self.assertTrue(isinstance(frame1_frame_parent, SlideFrameParent))

        # make sure the slide frame is the right size and in the right pos
        self.assertEqual(frame1_frame.size, [200, 100])
        self.assertEqual(frame1_frame.pos, [50, 50])

        # it's parent should be the same size and pos
        self.assertEqual(frame1_frame_parent.size, [200, 100])
        self.assertEqual(frame1_frame_parent.pos, [50, 50])

        # it's parent's parent is the display
        self.assertEqual(frame1_frame_parent.parent.size, [400, 300])
        self.assertEqual(frame1_frame_parent.parent.pos, [0, 0])

        # add a widget to the frame
        self.mc.events.post('show_frame_text')
        self.advance_time(1)

        # make sure the text is in the frame
        self.assertEqual(
            frame1_frame.current_slide.children[0].children[0].text,
            'SLIDE 1 IN FRAME')

        # flip frame to a different slide
        self.mc.events.post('show_frame_text2')
        self.advance_time(1)

        # make sure the next text is there
        self.assertEqual(
            frame1_frame.current_slide.children[0].children[0].text,
            'SLIDE 2 IN FRAME')

        # flip back to the first frame and make sure that text is there
        self.mc.events.post('show_frame_text')
        self.advance_time(1)

        self.assertEqual(
            frame1_frame.current_slide.children[0].children[0].text,
            'SLIDE 1 IN FRAME')

    def test_remove_non_existent_slide(self):
        self.assertFalse(self.mc.targets['default'].remove_slide('hello'))
        self.advance_time()

    def test_two_slides_in_one_tick(self):
        self.mock_event('slide_slide1_active')
        self.mock_event('slide_slide2_active')

        self.mc.events.post('show_slide1')
        self.mc.events.post('show_slide2')
        self.advance_time()

        self.assertEventNotCalled('slide_slide1_active')
        self.assertEventCalled('slide_slide2_active', 1)
