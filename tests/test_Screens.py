from .MpfMcTestCase import MpfMcTestCase
from mc.uix.screen import Screen


class TestScreens(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/screen'

    def get_config_file(self):
        return 'test_screens.yaml'

    def test_mc_screen_processor(self):
        self.assertIn('screen1', self.mc.machine_config['screens'])
        self.assertIn('screen2', self.mc.machine_config['screens'])
        self.assertIn('screen3', self.mc.machine_config['screens'])
        self.assertIn('screen4', self.mc.machine_config['screens'])
        self.assertIn('screen5', self.mc.machine_config['screens'])

    def test_mode_by_name(self):
        screen = Screen(mc=self.mc,
                        name='screen1',
                        config=self.mc.machine_config['screens']['screen1'],
                        screen_manager=self.mc.default_display.screen_manager,
                        mode='attract',
                        priority=0)

        self.assertIs(screen.mode, self.mc.modes['attract'])

    def test_mode_by_object(self):
        screen = Screen(mc=self.mc,
                        name='screen1',
                        config=self.mc.machine_config['screens']['screen1'],
                        screen_manager=self.mc.default_display.screen_manager,
                        mode=self.mc.modes['attract'],
                        priority=0)

        self.assertIs(screen.mode, self.mc.modes['attract'])

    def test_priority_passed(self):
        screen = Screen(mc=self.mc,
                        name='screen1',
                        config=self.mc.machine_config['screens']['screen1'],
                        screen_manager=self.mc.default_display.screen_manager,
                        mode=self.mc.modes['attract'],
                        priority=123)

        self.assertEqual(screen.priority, 123)

    def test_priority_from_mode(self):
        screen = Screen(mc=self.mc,
                        name='screen1',
                        config=self.mc.machine_config['screens']['screen1'],
                        screen_manager=self.mc.default_display.screen_manager,
                        mode=self.mc.modes['attract'])

        self.assertEqual(screen.priority, self.mc.modes['attract'].priority)

    def test_no_priority_no_mode(self):
        screen = Screen(mc=self.mc,
                        name='screen1',
                        config=self.mc.machine_config['screens']['screen1'],
                        screen_manager=self.mc.default_display.screen_manager)

        self.assertIs(screen.priority, 0)

    def test_widgets_from_config(self):
        screen = Screen(mc=self.mc,
                        name='screen1',
                        config=self.mc.machine_config['screens']['screen1'],
                        screen_manager=self.mc.default_display.screen_manager,
                        mode='attract',
                        priority=0)

        widget_tree = list()
        for s in screen.walk():
            widget_tree.append(s)

        # last widget is drawn last (on top), so the order should be flipped
        self.assertEqual(widget_tree[1].text, 'text3')
        self.assertEqual(widget_tree[2].text, 'text2')
        self.assertEqual(widget_tree[3].text, 'text1')

