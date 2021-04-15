from mpf.core.segment_mappings import SEVEN_SEGMENTS, FOURTEEN_SEGMENTS

from mpfmc.tests.MpfMcTestCase import MpfMcTestCase
from mpfmc.widgets.segment_display_emulator import SegmentDisplayEmulator


class TestSegmentDisplayEmulatorWidget(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/segment_display_widget'

    def get_config_file(self):
        return 'test_segment_display_widget.yaml'

    def test_character_encoding(self):
        self.assertEqual(2304,
                         SegmentDisplayEmulator.get_fourteen_segment_character_encoding(FOURTEEN_SEGMENTS[ord(')')]))
        self.assertEqual(11,
                         SegmentDisplayEmulator.get_seven_segment_character_encoding(SEVEN_SEGMENTS[ord(')')]))

    def test_segment_display(self):
        self.mc.events.post('show_top_display')
        self.mc.events.post('show_middle_display')
        self.mc.events.post('show_bottom_display')
        self.advance_real_time(1)
        self.mc.events.post('update_segment_display', number='1', text='GOODBYE')
        self.mc.events.post('update_segment_display', number='2', text='FOR NOW ')
        self.advance_real_time(0.033)
        self.assertIn('GOODBYE', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertIn('FOR NOW ', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.mc.events.post('update_segment_display', number='2', text='\x11               ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', number='2', text='\x12\x11              ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', number='2', text='\x13\x12\x11             ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', number='2', text='\x13\x13\x12\x11            ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', number='2', text='\x14\x13\x13\x12\x11           ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', number='2', text=' \x14\x13\x13\x12\x11          ')
        self.advance_real_time(0.033)
        self.assertIn(' \x14\x13\x13\x12\x11          ', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.mc.events.post('update_segment_display', number='2', text='W  \x14\x13\x13\x12\x11         ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', number='2', text='OW \x14\x13\x13\x12\x11        ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', number='2', text='NOW \x14\x13\x13\x12\x11       ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', number='2', text=' NOW \x14\x13\x13\x12\x11      ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', number='2', text='R NOW \x14\x13\x13\x12\x11     ')
        self.advance_real_time(0.033)
        self.assertIn('R NOW \x14\x13\x13\x12\x11     ', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.mc.events.post('update_segment_display', number='2', text='OR NOW \x14\x13\x13\x12\x11    ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', number='2', text='FOR NOW \x14\x13\x13\x12\x11   ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', number='2', text=' FOR NOW \x14\x13\x13\x12\x11  ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', number='2', text='  FOR NOW \x14\x13\x13\x12\x11 ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', number='2', text='   FOR NOW \x14\x13\x13\x12\x11')
        self.advance_real_time(1)
        self.assertIn('   FOR NOW \x14\x13\x13\x12\x11', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])

    def test_push_right_transition_steps(self):
        # push right
        transition_steps = SegmentDisplayEmulator.generate_push_right_transition([1, 2, 3, 4, 5],
                                                                                 [101, 102, 103, 104, 105])
        self.assertEqual(5, len(transition_steps))
        self.assertEqual([105, 1, 2, 3, 4], transition_steps[0])
        self.assertEqual([104, 105, 1, 2, 3], transition_steps[1])
        self.assertEqual([103, 104, 105, 1, 2], transition_steps[2])
        self.assertEqual([102, 103, 104, 105, 1], transition_steps[3])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[4])

    def test_push_left_transition_steps(self):
        # push left
        transition_steps = SegmentDisplayEmulator.generate_push_left_transition([1, 2, 3, 4, 5],
                                                                                [101, 102, 103, 104, 105])
        self.assertEqual(5, len(transition_steps))
        self.assertEqual([2, 3, 4, 5, 101], transition_steps[0])
        self.assertEqual([3, 4, 5, 101, 102], transition_steps[1])
        self.assertEqual([4, 5, 101, 102, 103], transition_steps[2])
        self.assertEqual([5, 101, 102, 103, 104], transition_steps[3])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[4])

    def test_cover_right_transition_steps(self):
        # cover right
        transition_steps = SegmentDisplayEmulator.generate_cover_right_transition([1, 2, 3, 4, 5],
                                                                                  [101, 102, 103, 104, 105])
        self.assertEqual(5, len(transition_steps))
        self.assertEqual([105, 2, 3, 4, 5], transition_steps[0])
        self.assertEqual([104, 105, 3, 4, 5], transition_steps[1])
        self.assertEqual([103, 104, 105, 4, 5], transition_steps[2])
        self.assertEqual([102, 103, 104, 105, 5], transition_steps[3])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[4])

    def test_cover_left_transition_steps(self):
        # cover left
        transition_steps = SegmentDisplayEmulator.generate_cover_left_transition([1, 2, 3, 4, 5],
                                                                                 [101, 102, 103, 104, 105])
        self.assertEqual(5, len(transition_steps))
        self.assertEqual([1, 2, 3, 4, 101], transition_steps[0])
        self.assertEqual([1, 2, 3, 101, 102], transition_steps[1])
        self.assertEqual([1, 2, 101, 102, 103], transition_steps[2])
        self.assertEqual([1, 101, 102, 103, 104], transition_steps[3])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[4])

    def test_uncover_right_transition_steps(self):
        # uncover right
        transition_steps = SegmentDisplayEmulator.generate_uncover_right_transition([1, 2, 3, 4, 5],
                                                                                    [101, 102, 103, 104, 105])
        self.assertEqual(5, len(transition_steps))
        self.assertEqual([101, 1, 2, 3, 4], transition_steps[0])
        self.assertEqual([101, 102, 1, 2, 3], transition_steps[1])
        self.assertEqual([101, 102, 103, 1, 2], transition_steps[2])
        self.assertEqual([101, 102, 103, 104, 1], transition_steps[3])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[4])

    def test_uncover_left_transition_steps(self):
        # uncover left
        transition_steps = SegmentDisplayEmulator.generate_uncover_left_transition([1, 2, 3, 4, 5],
                                                                                   [101, 102, 103, 104, 105])
        self.assertEqual(5, len(transition_steps))
        self.assertEqual([2, 3, 4, 5, 105], transition_steps[0])
        self.assertEqual([3, 4, 5, 104, 105], transition_steps[1])
        self.assertEqual([4, 5, 103, 104, 105], transition_steps[2])
        self.assertEqual([5, 102, 103, 104, 105], transition_steps[3])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[4])

    def test_wipe_right_transition_steps(self):
        # wipe right
        transition_steps = SegmentDisplayEmulator.generate_wipe_right_transition([1, 2, 3, 4, 5],
                                                                                 [101, 102, 103, 104, 105])
        self.assertEqual(5, len(transition_steps))
        self.assertEqual([101, 2, 3, 4, 5], transition_steps[0])
        self.assertEqual([101, 102, 3, 4, 5], transition_steps[1])
        self.assertEqual([101, 102, 103, 4, 5], transition_steps[2])
        self.assertEqual([101, 102, 103, 104, 5], transition_steps[3])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[4])

    def test_wipe_left_transition_steps(self):
        # wipe left
        transition_steps = SegmentDisplayEmulator.generate_wipe_left_transition([1, 2, 3, 4, 5],
                                                                                [101, 102, 103, 104, 105])
        self.assertEqual(5, len(transition_steps))
        self.assertEqual([1, 2, 3, 4, 105], transition_steps[0])
        self.assertEqual([1, 2, 3, 104, 105], transition_steps[1])
        self.assertEqual([1, 2, 103, 104, 105], transition_steps[2])
        self.assertEqual([1, 102, 103, 104, 105], transition_steps[3])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[4])

    def test_split_wipe_odd_transition_steps(self):
        # split wipe (odd display length)
        transition_steps = SegmentDisplayEmulator.generate_wipe_split_open_transition([1, 2, 3, 4, 5],
                                                                                      [101, 102, 103, 104, 105])
        self.assertEqual(3, len(transition_steps))
        self.assertEqual([1, 2, 103, 4, 5], transition_steps[0])
        self.assertEqual([1, 102, 103, 104, 5], transition_steps[1])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[2])

    def test_split_wipe_even_transition_steps(self):
        # wipe split open (even display length)
        transition_steps = SegmentDisplayEmulator.generate_wipe_split_open_transition([1, 2, 3, 4, 5, 6],
                                                                                      [101, 102, 103, 104, 105, 106])
        self.assertEqual(3, len(transition_steps))
        self.assertEqual([1, 2, 103, 104, 5, 6], transition_steps[0])
        self.assertEqual([1, 102, 103, 104, 105, 6], transition_steps[1])
        self.assertEqual([101, 102, 103, 104, 105, 106], transition_steps[2])

    def test_split_push_open_odd_transition_steps(self):
        # split push open (odd display length)
        transition_steps = SegmentDisplayEmulator.generate_push_split_open_transition([1, 2, 3, 4, 5],
                                                                                      [101, 102, 103, 104, 105])
        self.assertEqual(3, len(transition_steps))
        self.assertEqual([2, 3, 103, 4, 5], transition_steps[0])
        self.assertEqual([3, 102, 103, 104, 4], transition_steps[1])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[2])

    def test_split_push_open_even_transition_steps(self):
        # split push open (even display length)
        transition_steps = SegmentDisplayEmulator.generate_push_split_open_transition([1, 2, 3, 4, 5, 6],
                                                                                      [101, 102, 103, 104, 105, 106])
        self.assertEqual(3, len(transition_steps))
        self.assertEqual([2, 3, 103, 104, 4, 5], transition_steps[0])
        self.assertEqual([3, 102, 103, 104, 105, 4], transition_steps[1])
        self.assertEqual([101, 102, 103, 104, 105, 106], transition_steps[2])

    def test_split_push_close_odd_transition_steps(self):
        # split push close (odd display length)
        transition_steps = SegmentDisplayEmulator.generate_push_split_close_transition([1, 2, 3, 4, 5],
                                                                                       [101, 102, 103, 104, 105])
        self.assertEqual(3, len(transition_steps))
        self.assertEqual([103, 2, 3, 4, 104], transition_steps[0])
        self.assertEqual([102, 103, 3, 104, 105], transition_steps[1])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[2])

    def test_split_push_close_even_transition_steps(self):
        # split push close (even display length)
        transition_steps = SegmentDisplayEmulator.generate_push_split_close_transition([1, 2, 3, 4, 5, 6],
                                                                                       [101, 102, 103, 104, 105, 106])
        self.assertEqual(3, len(transition_steps))
        self.assertEqual([103, 2, 3, 4, 5, 104], transition_steps[0])
        self.assertEqual([102, 103, 3, 4, 104, 105], transition_steps[1])
        self.assertEqual([101, 102, 103, 104, 105, 106], transition_steps[2])
