from mpfmc.tests.MpfMcTestCase import MpfMcTestCase
from mpfmc.widgets.segment_display_emulator import SegmentDisplayEmulator
from mpf.core.segment_mappings import FOURTEEN_SEGMENTS


class TestSegmentDisplayEmulatorWidget(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/segment_display_widget'

    def get_config_file(self):
        return 'test_segment_display_widget.yaml'

    def test_character_encoding(self):
        self.assertEqual(2304, SegmentDisplayEmulator.get_character_encoding(FOURTEEN_SEGMENTS[ord(')')]))

    def test_segment_display(self):
        self.mc.events.post('show_top_display')
        self.mc.events.post('show_bottom_display')
        self.advance_real_time(4)
        self.mc.events.post('update_segment_display_1', text='GOODBYE')
        self.mc.events.post('update_segment_display_2', text='FOR NOW ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display_2', text='\x11               ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display_2', text='\x12\x11              ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display_2', text='\x13\x12\x11             ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display_2', text='\x13\x13\x12\x11            ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display_2', text='\x14\x13\x13\x12\x11           ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display_2', text=' \x14\x13\x13\x12\x11          ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display_2', text='W  \x14\x13\x13\x12\x11         ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display_2', text='OW \x14\x13\x13\x12\x11        ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display_2', text='NOW \x14\x13\x13\x12\x11       ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display_2', text=' NOW \x14\x13\x13\x12\x11      ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display_2', text='R NOW \x14\x13\x13\x12\x11     ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display_2', text='OR NOW \x14\x13\x13\x12\x11    ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display_2', text='FOR NOW \x14\x13\x13\x12\x11   ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display_2', text=' FOR NOW \x14\x13\x13\x12\x11  ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display_2', text='  FOR NOW \x14\x13\x13\x12\x11 ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display_2', text='   FOR NOW \x14\x13\x13\x12\x11')
        self.advance_real_time(4)

    def test_transition_steps(self):

        # push right
        transition_steps = SegmentDisplayEmulator.generate_push_transition([1, 2, 3, 4, 5],
                                                                           [101, 102, 103, 104, 105],
                                                                           True)
        self.assertEqual(5, len(transition_steps))
        self.assertEqual([105, 1, 2, 3, 4], transition_steps[0])
        self.assertEqual([104, 105, 1, 2, 3], transition_steps[1])
        self.assertEqual([103, 104, 105, 1, 2], transition_steps[2])
        self.assertEqual([102, 103, 104, 105, 1], transition_steps[3])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[4])

        # push left
        transition_steps = SegmentDisplayEmulator.generate_push_transition([1, 2, 3, 4, 5],
                                                                           [101, 102, 103, 104, 105],
                                                                           False)
        self.assertEqual(5, len(transition_steps))
        self.assertEqual([2, 3, 4, 5, 101], transition_steps[0])
        self.assertEqual([3, 4, 5, 101, 102], transition_steps[1])
        self.assertEqual([4, 5, 101, 102, 103], transition_steps[2])
        self.assertEqual([5, 101, 102, 103, 104], transition_steps[3])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[4])

        # cover right
        transition_steps = SegmentDisplayEmulator.generate_cover_transition([1, 2, 3, 4, 5],
                                                                            [101, 102, 103, 104, 105],
                                                                            True)
        self.assertEqual(5, len(transition_steps))
        self.assertEqual([105, 2, 3, 4, 5], transition_steps[0])
        self.assertEqual([104, 105, 3, 4, 5], transition_steps[1])
        self.assertEqual([103, 104, 105, 4, 5], transition_steps[2])
        self.assertEqual([102, 103, 104, 105, 5], transition_steps[3])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[4])

        # cover left
        transition_steps = SegmentDisplayEmulator.generate_cover_transition([1, 2, 3, 4, 5],
                                                                            [101, 102, 103, 104, 105],
                                                                            False)
        self.assertEqual(5, len(transition_steps))
        self.assertEqual([1, 2, 3, 4, 101], transition_steps[0])
        self.assertEqual([1, 2, 3, 101, 102], transition_steps[1])
        self.assertEqual([1, 2, 101, 102, 103], transition_steps[2])
        self.assertEqual([1, 101, 102, 103, 104], transition_steps[3])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[4])

        # uncover right
        transition_steps = SegmentDisplayEmulator.generate_uncover_transition([1, 2, 3, 4, 5],
                                                                              [101, 102, 103, 104, 105],
                                                                              True)
        self.assertEqual(5, len(transition_steps))
        self.assertEqual([101, 1, 2, 3, 4], transition_steps[0])
        self.assertEqual([101, 102, 1, 2, 3], transition_steps[1])
        self.assertEqual([101, 102, 103, 1, 2], transition_steps[2])
        self.assertEqual([101, 102, 103, 104, 1], transition_steps[3])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[4])

        # uncover left
        transition_steps = SegmentDisplayEmulator.generate_uncover_transition([1, 2, 3, 4, 5],
                                                                              [101, 102, 103, 104, 105],
                                                                              False)
        self.assertEqual(5, len(transition_steps))
        self.assertEqual([2, 3, 4, 5, 105], transition_steps[0])
        self.assertEqual([3, 4, 5, 104, 105], transition_steps[1])
        self.assertEqual([4, 5, 103, 104, 105], transition_steps[2])
        self.assertEqual([5, 102, 103, 104, 105], transition_steps[3])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[4])

        # wipe right
        transition_steps = SegmentDisplayEmulator.generate_wipe_transition([1, 2, 3, 4, 5],
                                                                           [101, 102, 103, 104, 105],
                                                                           True)
        self.assertEqual(5, len(transition_steps))
        self.assertEqual([101, 2, 3, 4, 5], transition_steps[0])
        self.assertEqual([101, 102, 3, 4, 5], transition_steps[1])
        self.assertEqual([101, 102, 103, 4, 5], transition_steps[2])
        self.assertEqual([101, 102, 103, 104, 5], transition_steps[3])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[4])

        # wipe left
        transition_steps = SegmentDisplayEmulator.generate_wipe_transition([1, 2, 3, 4, 5],
                                                                           [101, 102, 103, 104, 105],
                                                                           False)
        self.assertEqual(5, len(transition_steps))
        self.assertEqual([1, 2, 3, 4, 105], transition_steps[0])
        self.assertEqual([1, 2, 3, 104, 105], transition_steps[1])
        self.assertEqual([1, 2, 103, 104, 105], transition_steps[2])
        self.assertEqual([1, 102, 103, 104, 105], transition_steps[3])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[4])

        # split wipe (odd display length)
        transition_steps = SegmentDisplayEmulator.generate_wipe_split_transition([1, 2, 3, 4, 5],
                                                                                 [101, 102, 103, 104, 105])
        self.assertEqual(3, len(transition_steps))
        self.assertEqual([1, 2, 103, 4, 5], transition_steps[0])
        self.assertEqual([1, 102, 103, 104, 5], transition_steps[1])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[2])

        # wipe split open (even display length)
        transition_steps = SegmentDisplayEmulator.generate_wipe_split_transition([1, 2, 3, 4, 5, 6],
                                                                                 [101, 102, 103, 104, 105, 106])
        self.assertEqual(3, len(transition_steps))
        self.assertEqual([1, 2, 103, 104, 5, 6], transition_steps[0])
        self.assertEqual([1, 102, 103, 104, 105, 6], transition_steps[1])
        self.assertEqual([101, 102, 103, 104, 105, 106], transition_steps[2])

        # push split open (odd display length)
        transition_steps = SegmentDisplayEmulator.generate_push_split_open_transition([1, 2, 3, 4, 5],
                                                                                      [101, 102, 103, 104, 105])
        self.assertEqual(3, len(transition_steps))
        self.assertEqual([2, 3, 103, 4, 5], transition_steps[0])
        self.assertEqual([3, 102, 103, 104, 4], transition_steps[1])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[2])

        # split push open (even display length)
        transition_steps = SegmentDisplayEmulator.generate_push_split_open_transition([1, 2, 3, 4, 5, 6],
                                                                                      [101, 102, 103, 104, 105, 106])
        self.assertEqual(3, len(transition_steps))
        self.assertEqual([2, 3, 103, 104, 4, 5], transition_steps[0])
        self.assertEqual([3, 102, 103, 104, 105, 4], transition_steps[1])
        self.assertEqual([101, 102, 103, 104, 105, 106], transition_steps[2])

        # split push close (odd display length)
        transition_steps = SegmentDisplayEmulator.generate_push_split_close_transition([1, 2, 3, 4, 5],
                                                                                       [101, 102, 103, 104, 105])
        self.assertEqual(3, len(transition_steps))
        self.assertEqual([103, 2, 3, 4, 104], transition_steps[0])
        self.assertEqual([102, 103, 3, 104, 105], transition_steps[1])
        self.assertEqual([101, 102, 103, 104, 105], transition_steps[2])

        # split push close (even display length)
        transition_steps = SegmentDisplayEmulator.generate_push_split_close_transition([1, 2, 3, 4, 5, 6],
                                                                                       [101, 102, 103, 104, 105, 106])
        self.assertEqual(3, len(transition_steps))
        self.assertEqual([103, 2, 3, 4, 5, 104], transition_steps[0])
        self.assertEqual([102, 103, 3, 4, 104, 105], transition_steps[1])
        self.assertEqual([101, 102, 103, 104, 105, 106], transition_steps[2])

