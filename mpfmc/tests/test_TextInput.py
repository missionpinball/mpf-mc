from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestText(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/text_input'

    def get_config_file(self):
        return 'text_input.yaml'

    def test_text_input(self):
        self.mc.events.post('slide1')
        self.advance_time(1)

        text_input_widget = (
            self.mc.targets['default'].current_slide.widgets[1].widget)

        text_display_widget = (
            self.mc.targets['default'].current_slide.widgets[2].widget)

        self.assertEqual(text_display_widget.text, '')
        self.assertEqual(text_input_widget.text, 'C')
        self.advance_time()

        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'B')
        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'A')
        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'END')
        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'BACK')

        # should not crash if we go back with no chars
        self.mc.events.post('sw_start')
        self.advance_time()

        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'SPACE')
        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, '-')
        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, '_')

        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, '-')

        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'SPACE')

        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'BACK')

        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'END')

        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'A')

        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'B')

        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'C')

        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'D')

        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'E')

        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'F')

        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()

        self.assertEqual(text_input_widget.text, 'K')

        self.mc.events.post('sw_left_flipper')
        self.advance_time()

        self.assertEqual(text_input_widget.text, 'J')

        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()

        self.assertEqual(text_input_widget.text, 'M')

        self.mc.events.post('sw_start')
        self.advance_time()

        self.assertEqual(text_input_widget.text, 'M')
        self.assertEqual(text_display_widget.text, 'M')

        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_start')
        self.advance_time()

        self.assertEqual(text_input_widget.text, 'Q')
        self.assertEqual(text_display_widget.text, 'MQ')

        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()

        self.assertEqual(text_input_widget.text, 'BACK')

        self.mc.events.post('sw_start')
        self.advance_time()

        self.assertEqual(text_input_widget.text, 'Q')
        self.assertEqual(text_display_widget.text, 'M')

        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.mc.events.post('sw_start')
        self.advance_time()

        self.assertEqual(text_input_widget.text, 'P')
        self.assertEqual(text_display_widget.text, 'MP')

        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.mc.events.post('sw_left_flipper')
        self.advance_time()

        self.mc.events.post('sw_start')
        self.advance_time()

        self.assertEqual(text_input_widget.text, 'END')
        self.mc.events.post('sw_start')
        self.advance_time()
        self.assertEqual(text_display_widget.text, 'MPF')

    def test_text_input_blocking(self):
        self.mc.events.post('slide1')
        self.advance_time(1)

        text_input_widget = (
            self.mc.targets['default'].current_slide.widgets[1].widget)

        text_display_widget = (
            self.mc.targets['default'].current_slide.widgets[2].widget)

        self.assertEqual(text_display_widget.text, '')
        self.assertEqual(text_input_widget.text, 'C')
        self.advance_time()

        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'B')
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'C')
        self.mc.events.post('test_block')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'C')
        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'C')
        self.mc.events.post('test_release')
        self.advance_time()
        self.mc.events.post('sw_right_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'D')
        self.mc.events.post('sw_left_flipper')
        self.advance_time()
        self.assertEqual(text_input_widget.text, 'C')
