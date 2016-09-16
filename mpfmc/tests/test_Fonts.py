from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestDmd(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/fonts'

    def get_config_file(self):
        return 'built_in_dmd_fonts.yaml'

    def test_dmd(self):

        self.mc.events.post('window_slide')

        self.mc.events.post('dmd_big')
        self.advance_time(1)

        # make sure the adjustments are correct
        top_widget = self.mc.displays['dmd'].current_slide.stencil.children[0]
        bottom_widget = self.mc.displays['dmd'].current_slide.stencil.children[1]

        self.assertEqual(
            self.mc.machine_config['widget_styles']['dmd_big']['adjust_bottom'],
            bottom_widget.y * -1)

        self.assertEqual(
            self.mc.machine_config['widget_styles']['dmd_big']['adjust_top'],
            (32 - top_widget.height - top_widget.y) * -1)

        self.mc.events.post('dmd_med')
        self.advance_time(1)

        # make sure the adjustments are correct
        top_widget = self.mc.displays['dmd'].current_slide.stencil.children[0]
        bottom_widget = self.mc.displays['dmd'].current_slide.stencil.children[1]

        self.assertEqual(
            self.mc.machine_config['widget_styles']['dmd_med']['adjust_bottom'],
            bottom_widget.y * -1)

        self.assertEqual(
            self.mc.machine_config['widget_styles']['dmd_med']['adjust_top'],
            (32 - top_widget.height - top_widget.y) * -1)

        self.mc.events.post('dmd_small')
        self.advance_time(1)

        # make sure the adjustments are correct
        top_widget = self.mc.displays['dmd'].current_slide.stencil.children[0]
        bottom_widget = self.mc.displays['dmd'].current_slide.stencil.children[1]

        self.assertEqual(
            self.mc.machine_config['widget_styles']['dmd_small']['adjust_bottom'],
            bottom_widget.y * -1)

        self.assertEqual(
            self.mc.machine_config['widget_styles']['dmd_small']['adjust_top'],
            (32 - top_widget.height - top_widget.y) * -1)
