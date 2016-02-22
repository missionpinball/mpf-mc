from mpfmc.uix.display import Display
from mpfmc.uix.slide_frame import SlideFrame
from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestDisplaySingle(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/display'

    def get_config_file(self):
        return 'test_display_none.yaml'

    def test_mc_display_none(self):
        # Make sure a single display is loaded properly:

        self.assertIn('default', self.mc.displays)
        self.assertEqual(self.mc.displays['default'].size, [1, 1])
        self.assertEqual(self.mc.targets['default'].parent.parent.parent,
                         self.mc.displays['default'])

