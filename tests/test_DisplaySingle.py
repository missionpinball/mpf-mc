from mc.uix.display import Display
from mc.uix.slide_frame import SlideFrame
from .MpfMcTestCase import MpfMcTestCase


class TestDisplaySingle(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/display'

    def get_config_file(self):
        return 'test_display_single.yaml'

    def test_mc_display(self):
        # Make sure a single display is loaded properly:

        self.assertIn('window', self.mc.displays)
        self.assertTrue(isinstance(self.mc.displays['window'], Display))
        self.assertEqual(self.mc.displays['window'].size, [401, 301])
        self.assertEqual(self.mc.targets['default'], self.mc.targets[
            'window'])

        # walk the display's widget tree and make sure everything is right
        widget_hierarchy = ['display', 'slide_frame']
        for widget, name in zip(self.mc.displays['window'].walk(),
                                widget_hierarchy):
            getattr(self, 'check_{}'.format(name))(widget=widget)

    def check_display(self, widget):
        self.assertTrue(isinstance(widget, Display))

    def check_slide_frame(self, widget):
        self.assertTrue(isinstance(widget, SlideFrame))
        self.assertEqual(widget.size, [401, 301])
