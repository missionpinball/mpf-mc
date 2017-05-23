from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestColor(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/color'

    def get_config_file(self):
        return 'test_color.yaml'

    def get_widget(self, index=0):
        return self.mc.targets['default'].current_slide.children[index].widget

    def test_colors(self):
        self.mc.events.post('slide1')
        self.advance_time()

        self.assertEqual(self.get_widget().color, [1.0, 0, 0, 1.0])
        self.assertEqual(self.get_widget(1).color[0], 0)
        self.assertEqual(self.get_widget(1).color[1], 0)
        self.assertEqual(self.get_widget(1).color[2], 1.0)
        self.assertAlmostEqual(self.get_widget(1).color[3], 0.5, delta=0.1)
        self.assertEqual(self.get_widget(2).color, [0, 1.0, 0, 1.0])
