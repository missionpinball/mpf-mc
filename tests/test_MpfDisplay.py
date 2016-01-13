from kivy.app import App
from kivy.clock import Clock

from .MpfMcTestCase import MpfMcTestCase


class TestMcDisplays(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/display'

    def get_config_file(self):
        return 'test_mc_displays_single.yaml'

    def test_mc_display(self):
        print(self.mc.displays)
        print(self.mc.default_display.size)

        # a = App()
        # Clock.schedule_once(self.mc.stop, 1)
        # a.run()
