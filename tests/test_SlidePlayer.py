from .MpfMcTestCase import MpfMcTestCase


class TestSlidePlayer(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/slide_player'

    def get_config_file(self):
        return 'test_slide_player.yaml'

    def test_slide_on_default_display(self):
        self.mc.events.post('show_slide_1')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')

        # now replace that slide at the same priority and make sure it works
        self.mc.events.post('show_slide_4')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_4')

    def test_slide_on_default_display_hardcoded(self):
        self.mc.events.post('show_slide_2')
        self.advance_time()
        self.assertEqual(self.mc.displays['display1'].current_slide_name,
                         'machine_slide_2')

    def test_slide_on_second_display(self):
        self.mc.events.post('show_slide_3')
        self.advance_time()
        self.assertEqual(self.mc.displays['display2'].current_slide_name,
                         'machine_slide_3')

    def test_priority_from_slide_player(self):
        self.mc.events.post('show_slide_4_p200')
        self.advance_time()
        self.assertEqual(self.mc.displays['display1'].current_slide_name,
                         'machine_slide_4')
        self.assertEqual(self.mc.displays['display1'].current_slide.priority,
                         200)

    def test_force_slide(self):
        self.mc.events.post('show_slide_4_p200')
        self.advance_time()
        self.assertEqual(self.mc.displays['display1'].current_slide_name,
                         'machine_slide_4')
        self.assertEqual(self.mc.displays['display1'].current_slide.priority,
                         200)

        self.mc.events.post('show_slide_1_force')
        self.advance_time()
        self.assertEqual(self.mc.displays['display1'].current_slide_name,
                         'machine_slide_1')
        self.assertEqual(self.mc.displays['display1'].current_slide.priority,
                         0)

    def test_dont_show_slide(self):
        self.mc.events.post('show_slide_1')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')
        self.assertEqual(self.mc.displays['display1'].current_slide.priority,
                         0)

        # request a higher priority slide, but don't show it
        self.mc.events.post('show_slide_5_dont_show')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')
        self.assertEqual(self.mc.displays['display1'].current_slide.priority,
                         0)
