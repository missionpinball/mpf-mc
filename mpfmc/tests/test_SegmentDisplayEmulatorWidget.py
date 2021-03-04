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
        self.mc.events.post('update_display')
        self.advance_real_time(5)

