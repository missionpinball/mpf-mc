from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestText(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/text_input'

    def get_config_file(self):
        return 'text_input.yaml'

    def test_text_input(self):
        self.mc.events.post('slide1')
        self.advance_time()

        text_input_widget = (
            self.mc.targets['default'].current_slide.children[0].children[1])

        text_display_widget = (
            self.mc.targets['default'].current_slide.children[0].children[2])

        self.assertEqual(text_display_widget.text, '')
        self.assertEqual(text_input_widget.text, 'C')
        self.advance_time()

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

        self.assertEqual(text_input_widget.text, '')
        self.assertEqual(text_display_widget.text, 'MPF')
