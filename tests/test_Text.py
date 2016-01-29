from tests.MpfMcTestCase import MpfMcTestCase


class TestText(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/text'

    def get_config_file(self):
        return 'test_text.yaml'

    def get_widget(self):
        return self.mc.targets['default'].current_slide.children[0]

    def test_static_text(self):
        # Very basic test
        self.mc.events.post('static_text')
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'TEST')

    def test_text_from_event_param1(self):
        # widget text is only from event param
        self.mc.events.post('text_from_event_param1', param1='HELLO')
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'HELLO')

    def test_text_from_event_param2(self):
        # widget text puts static text before param text
        self.mc.events.post('text_from_event_param2', param1='HELLO')
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'HI HELLO')

    def test_text_from_event_param3(self):
        # widget text puts static text before and after param text
        self.mc.events.post('text_from_event_param3', param1='AND')
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'MIX AND MATCH')

    def test_text_from_event_param4(self):
        # static and event text with no space between
        self.mc.events.post('text_from_event_param4', param1='SPACE')
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'NOSPACE')

    def test_text_from_event_param5(self):
        #test event text that comes in as non-string
        self.mc.events.post('text_from_event_param5', param1=1)
        self.advance_time()

        self.assertEqual(self.get_widget().text, 'NUMBER 1')

    def test_text_from_event_param6(self):
        # placeholder for event text for a param that doesn't exist
        self.mc.events.post('text_from_event_param6')
        self.advance_time()

        self.assertEqual(self.get_widget().text, '%param1%')

    def test_text_from_event_param7(self):
        # test percent sign hard coded
        self.mc.events.post('text_from_event_param7')
        self.advance_time()

        self.assertEqual(self.get_widget().text, '100%')

    def test_text_from_event_param8(self):
        # test perent next to placeholder text
        self.mc.events.post('text_from_event_param8', param1=100)
        self.advance_time()

        self.assertEqual(self.get_widget().text, '100%')

