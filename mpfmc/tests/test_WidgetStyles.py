from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestWidgetStyles(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/widget_styles'

    def get_config_file(self):
        return 'test_widget_styles.yaml'

    def get_widget(self, index=0):
        return self.mc.targets['default'].current_slide.children[0].children[index]

    def test_style_loading(self):
        self.assertIn('text_default', self.mc.machine_config['widget_styles'])

    def test_style(self):
        self.mc.events.post('slide1')
        self.advance_time()

        # Test named style

        # font size set in style
        self.assertEqual(self.get_widget().font_size, 100)

        # halign set in style and widget, widget should win
        self.assertEqual(self.get_widget().halign, 'right')

        # second widget has no style set, so it should get the default
        self.assertEqual(self.get_widget(1).font_size, 21)

    def test_default_style(self):
        self.mc.events.post('slide3')
        self.advance_time()

        self.assertEqual(self.get_widget().color, [1, 0, 0, 1])

    def test_invalid_style(self):
        self.mc.events.post('slide4')

        with self.assertRaises(ValueError):
            self.advance_time()

    def test_local_setting_overrides_style(self):
        self.mc.events.post('slide5')
        self.advance_time()

        self.assertEqual(self.get_widget().font_size, 50)

    # todo some future release

    # def test_mode_style(self):
    #     self.mc.modes['mode1'].start()
    #     self.advance_time()
    #
    #     self.mc.events.post('slide2')
    #     self.advance_time()
    #
    #     # widget with no style, should pickup default out of the mode
    #     # text_strings, rather than the machine wide one
    #     self.assertEqual(self.get_widget().font_size, 50)
    #
    #     # mode widget with style from machine wide config
    #     self.assertEqual(self.get_widget(1).font_size, 100)
    #
    #     # mode widget with style name that's not valid, so it should
    #     # pickup the default
    #     self.assertEqual(self.get_widget(2).font_size, 50)
