from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestFonts(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/fonts'

    def get_config_file(self):
        return 'built_in_dmd_fonts.yaml'

    def test_dmd_font_styles(self):

        self.mc.events.post('window_slide')
        self.advance_time(1)

        self.mc.events.post('dmd_big')
        self.advance_time(1)

        # Make sure the dmd_big style hasn't changed
        self.assertEqual(self.mc.machine_config['widget_styles']['big']['adjust_bottom'], 5)
        self.assertEqual(self.mc.machine_config['widget_styles']['big']['adjust_top'], 2)
        self.assertEqual(self.mc.machine_config['widget_styles']['big']['font_size'], 10)

        # make sure the adjustments are correct
        top_widget = self.mc.displays['dmd'].current_slide.widgets[0].widget
        bottom_widget = self.mc.displays['dmd'].current_slide.widgets[1].widget

        self.assertEqual(bottom_widget.anchor_y, 'bottom')
        self.assertEqual(
            self.mc.machine_config['widget_styles']['big']['adjust_bottom'],
            -bottom_widget.anchor_offset_pos[1])

        self.assertEqual(top_widget.anchor_y, 'top')
        self.assertEqual(top_widget.anchor_offset_pos[1], -top_widget.height +
                         self.mc.machine_config['widget_styles']['big']['adjust_top'])

        self.mc.events.post('dmd_med')
        self.advance_time(1)

        # Make sure the dmd_med style hasn't changed
        self.assertEqual(self.mc.machine_config['widget_styles']['medium']['adjust_bottom'], 1)
        self.assertEqual(self.mc.machine_config['widget_styles']['medium']['adjust_top'], 1)
        self.assertEqual(self.mc.machine_config['widget_styles']['medium']['font_size'], 8)

        # make sure the adjustments are correct
        top_widget = self.mc.displays['dmd'].current_slide.widgets[0].widget
        bottom_widget = self.mc.displays['dmd'].current_slide.widgets[1].widget

        self.assertEqual(bottom_widget.anchor_y, 'bottom')
        self.assertEqual(
            self.mc.machine_config['widget_styles']['medium']['adjust_bottom'],
            -bottom_widget.anchor_offset_pos[1])

        self.assertEqual(top_widget.anchor_y, 'top')
        self.assertEqual(top_widget.anchor_offset_pos[1], -top_widget.height +
                         self.mc.machine_config['widget_styles']['medium']['adjust_top'])

        self.mc.events.post('dmd_small')
        self.advance_time(1)

        # Make sure the dmd_small style hasn't changed
        self.assertEqual(self.mc.machine_config['widget_styles']['small']['adjust_bottom'], 3)
        self.assertEqual(self.mc.machine_config['widget_styles']['small']['adjust_top'], 2)
        self.assertEqual(self.mc.machine_config['widget_styles']['small']['font_size'], 9)

        # make sure the adjustments are correct
        top_widget = self.mc.displays['dmd'].current_slide.widgets[0].widget
        bottom_widget = self.mc.displays['dmd'].current_slide.widgets[1].widget

        self.assertEqual(bottom_widget.anchor_y, 'bottom')
        self.assertEqual(
            self.mc.machine_config['widget_styles']['small']['adjust_bottom'],
            -bottom_widget.anchor_offset_pos[1])

        self.assertEqual(top_widget.anchor_y, 'top')
        self.assertEqual(top_widget.anchor_offset_pos[1], -top_widget.height +
                         self.mc.machine_config['widget_styles']['small']['adjust_top'])
