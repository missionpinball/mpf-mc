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
        self.mc.events.post('update_segment_display', segment_display_name='display1', text='GOODBYE')
        self.mc.events.post('update_segment_display', segment_display_name='display2', text='FOR NOW ')
        self.advance_real_time(0.033)
        self.assertIn('GOODBYE', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.assertIn('FOR NOW ', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.mc.events.post('update_segment_display', segment_display_name='display2', text='\x11               ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', segment_display_name='display2', text='\x12\x11              ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', segment_display_name='display2',
                            text='\x13\x12\x11             ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', segment_display_name='display2',
                            text='\x13\x13\x12\x11            ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', segment_display_name='display2',
                            text='\x14\x13\x13\x12\x11           ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', segment_display_name='display2',
                            text=' \x14\x13\x13\x12\x11          ')
        self.advance_real_time(0.033)
        self.assertIn(' \x14\x13\x13\x12\x11          ', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.mc.events.post('update_segment_display', segment_display_name='display2',
                            text='W  \x14\x13\x13\x12\x11         ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', segment_display_name='display2',
                            text='OW \x14\x13\x13\x12\x11        ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', segment_display_name='display2',
                            text='NOW \x14\x13\x13\x12\x11       ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', segment_display_name='display2',
                            text=' NOW \x14\x13\x13\x12\x11      ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', segment_display_name='display2',
                            text='R NOW \x14\x13\x13\x12\x11     ')
        self.advance_real_time(0.033)
        self.assertIn('R NOW \x14\x13\x13\x12\x11     ', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
        self.mc.events.post('update_segment_display', segment_display_name='display2',
                            text='OR NOW \x14\x13\x13\x12\x11    ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', segment_display_name='display2',
                            text='FOR NOW \x14\x13\x13\x12\x11   ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', segment_display_name='display2',
                            text=' FOR NOW \x14\x13\x13\x12\x11  ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', segment_display_name='display2',
                            text='  FOR NOW \x14\x13\x13\x12\x11 ')
        self.advance_real_time(0.033)
        self.mc.events.post('update_segment_display', segment_display_name='display2',
                            text='   FOR NOW \x14\x13\x13\x12\x11')
        self.advance_real_time(1)
        self.assertIn('   FOR NOW \x14\x13\x13\x12\x11', [x.widget.text for x in self.mc.targets[
            'default'].current_slide.widgets])
