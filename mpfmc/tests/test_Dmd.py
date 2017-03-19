from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestDmd(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/dmd'

    def get_config_file(self):
        return 'test_dmd.yaml'

    def test_dmd(self):

        self.assertIn('dmd', self.mc.targets)

        self.mc.events.post('container_slide')
        self.mc.events.post('dmd_slide')
        self.advance_time(2)

    def test_positioning_named_widgets_on_dmd(self):

        self.assertIn('dmd', self.mc.targets)

        self.mc.events.post('container_slide')
        self.mc.events.post('position_widget_left')
        self.advance_time(.1)
        self.mc.events.post('position_widget_right')
        self.advance_time(.1)
        self.mc.events.post('position_widget_top')
        self.advance_time(.1)
        self.mc.events.post('position_widget_bottom')
        self.advance_time(.1)

        left = self.mc.displays['dmd'].children[0].children[0].children[3]
        right = self.mc.displays['dmd'].children[0].children[0].children[2]
        top = self.mc.displays['dmd'].children[0].children[0].children[1]
        bottom = self.mc.displays['dmd'].children[0].children[0].children[0]

        self.assertEqual(left.text, 'Left Widget')
        self.assertEqual(right.text, 'Right Widget')
        self.assertEqual(top.text, 'Top Widget')
        self.assertEqual(bottom.text, 'Bottom Widget')

        self.assertGreater(right.x, bottom.x)
        self.assertLess(left.x, bottom.x)
        self.assertGreater(top.y, left.y)
        self.assertLess(bottom.y, left.y)
