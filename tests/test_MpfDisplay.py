from .MpfMcTestCase import KmcTestCase


class TestKmcDisplays(KmcTestCase):

    def get_machine_path(self):
        return 'tests/machine_files/mc'

    def get_config_file(self):
        return 'test_mc_displays_single.yaml'

    def test_mc_display(self):
        print(self.mc.displays)
        print(self.mc.displays['window'])
        print(self.mc.displays['window'].size)
