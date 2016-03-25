import json

from mpf.core.bcp import decode_command_string
from mpf.core.config_player import ConfigPlayer
from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


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

    def test_mode_slide_player(self):
        # set a baseline slide
        self.mc.events.post('show_slide_1')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')

        # post the slide_player event from the mode. Should not show the slide
        # since the mode is not running
        self.mc.events.post('show_mode1_slide')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')

        # start the mode and then post that event again. The slide should
        # switch
        self.mc.modes['mode1'].start()
        self.mc.events.post('show_mode1_slide')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'mode1_slide')

        # stop the mode and make sure the slide is removed
        num_slides = len(self.mc.targets['display1'].slides)
        self.mc.modes['mode1'].stop()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')
        self.assertEqual(len(self.mc.targets['display1'].slides),
                         num_slides - 1)

        # post the slide_player event from the mode. Should not show the slide
        # since the mode is not running
        self.mc.events.post('show_mode1_slide')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')

        # show a priority 200 slide from the machine config
        self.mc.events.post('show_slide_4_p200')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_4')
        self.assertEqual(self.mc.targets['display1'].current_slide.priority,
                         200)

        # start the mode again (priority 500)
        self.mc.modes['mode1'].start()

        # show a slide, but priority 150 which means the slide will not be
        # shown
        self.mc.events.post('show_mode1_slide_2')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_4')
        self.assertEqual(self.mc.targets['display1'].current_slide.priority,
                         200)

        # now kill the current slide and the mode slide should show
        self.mc.targets['display1'].remove_slide('machine_slide_4')
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'mode1_slide_2')
        self.assertEqual(self.mc.targets['display1'].current_slide.priority,
                         150)

    def test_from_show_via_bcp(self):
        from mpf.core.bcp import encode_command_string

        show_slide_section = dict()
        show_slide_section['widgets'] = list()

        show_slide_section['widgets'].append(dict(
            type='text', text='TEST FROM SHOW'))

        show_slide_section = ConfigPlayer.show_players[
            'slides'].validate_show_config('slide1', show_slide_section, False)

        bcp_string = encode_command_string('trigger', name='slides_play',
                                           **show_slide_section)

        self.mc.bcp_processor.receive_bcp_message(bcp_string)
        self.advance_time(1)

    def test_slides_created_in_slide_player(self):
        # Anon slides are where the widgets are listed in the slide_player
        # section of a config file or the slides section of a show

        self.mc.events.post('anon_slide_dict')
        self.advance_time(1)

        self.mc.events.post('anon_slide_list')
        self.advance_time(1)

        self.mc.events.post('anon_slide_widgets')
        self.advance_time(1)
