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
