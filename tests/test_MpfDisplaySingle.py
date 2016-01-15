from mc.uix.display import MpfDisplay
from mc.uix.screen_manager import ScreenManager
from .MpfMcTestCase import MpfMcTestCase


class TestMpfDisplaySingle(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/display'

    def get_config_file(self):
        return 'test_mpfdisplay_single.yaml'

    def test_mc_display(self):
        # Make sure a single display is loaded properly:

        self.assertIn('window', self.mc.displays)
        self.assertTrue(isinstance(self.mc.displays['window'], MpfDisplay))
        self.assertEqual(self.mc.displays['window'].size, [401, 301])
        self.assertEqual(self.mc.default_display, self.mc.displays['window'])

        # walk the display's widget tree and make sure everything is right
        widget_hierarchy = ['display', 'screen_manager']
        for widget, name in zip(self.mc.default_display.walk(),
                                widget_hierarchy):
            getattr(self, 'check_{}'.format(name))(widget=widget)

    def check_display(self, widget):
        self.assertTrue(isinstance(widget, MpfDisplay))

    def check_screen_manager(self, widget):
        self.assertTrue(isinstance(widget, ScreenManager))
        self.assertEqual(widget.size, [401, 301])
