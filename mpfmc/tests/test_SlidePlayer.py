import weakref

import gc
from kivy.uix.screenmanager import WipeTransition, FadeTransition

from mpfmc.tests.MpfMcTestCase import MpfMcTestCase
from mpfmc.transitions.move_in import MoveInTransition
from mpf.tests.MpfTestCase import MpfTestCase

import mpfmc.core
import os


class TestSlidePlayer(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/slide_player'

    def get_config_file(self):
        return 'test_slide_player.yaml'

    def test_slide_with_vars(self):
        self.mc.events.post('show_slide_with_var')
        self.advance_time()
        self.assertEqual("SLIDE WITH VAR asd", self.mc.targets["default"].current_slide.children[0].children[0].text)

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

    def test_slide_on_disabled_display(self):
        self.mc.events.post('show_slide_display3')
        self.advance_time()
        self.assertNotEqual(self.mc.displays['display3'].current_slide_name, 'machine_slide_1')

    def test_animation(self):
        self.mc.events.post("show_slide_with_animations")
        self.advance_time()
        self.assertEqual(self.mc.displays['display1'].current_slide_name,
                         'my_slide')
        slide = weakref.ref(self.mc.targets['display1'].current_slide)
        self.assertTrue(slide())

        self.mc.events.post("remove_slide_with_animations")
        self.advance_time()
        self.assertEqual(self.mc.displays['display1'].current_slide_name,
                         'display1_blank')

        self.mc.events.post('show_slide_1')
        self.advance_time()

        gc.collect()
        self.advance_time()
        self.assertFalse(slide())

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
        slide = weakref.ref(self.mc.targets['display1'].current_slide)
        self.assertTrue(slide())
        # stop the mode and make sure the slide is removed
        num_slides = len(self.mc.targets['display1'].slides)
        self.mc.modes['mode1'].stop()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')
        self.assertEqual(len(self.mc.targets['display1'].slides),
                         num_slides - 1)

        self.advance_time(.1)

        gc.collect()
        self.assertFalse(slide())

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

    def test_slides_created_in_slide_player(self):
        # Anon slides are where the widgets are listed in the slide_player
        # section of a config file or the slides section of a show

        self.mc.events.post('anon_slide_dict')
        self.advance_time()

        self.mc.events.post('anon_slide_list')
        self.advance_time()

        self.mc.events.post('anon_slide_widgets')
        self.advance_time()

        slide = weakref.ref(self.mc.targets['display1'].current_slide)
        self.assertTrue(slide())

        self.mc.events.post('anon_slide_widgets2')
        self.advance_time(1)
        slide2 = weakref.ref(self.mc.targets['display1'].current_slide)

        gc.collect()

        self.assertFalse(slide())
        self.assertTrue(slide2())

    def test_expire_in_slide(self):
        # tests that slide expire time works when configured in a slide
        self.mc.events.post('base_slide_no_expire')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_6')

        self.mc.events.post('show_slide_7')  # expire 1s
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_7')

        self.advance_time(1)
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_6')

    def test_expire_in_slide_player(self):
        # tests that expire time works when configured in the slide player
        self.mc.events.post('base_slide_no_expire')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_6')

        self.mc.events.post('new_slide_expire')  # expire 1s
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')

        self.advance_time(1)
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_6')

    def test_expire_with_transition_out_in_slide(self):
        # Tests a slide expiring where the expiring slide has a transition
        self.mc.events.post('base_slide_no_expire')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_6')

        # show a slide which expires in 1 sec, and has a transition out set
        self.mc.events.post('show_slide_8')
        self.advance_time(.1)
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_8')

        # advance to after this slide_8 expired, transition should be in effect
        self.advance_time(1)
        self.assertTrue(isinstance(self.mc.targets['display1'].transition,
                                   WipeTransition))

        # advance to transition done, should be back to the original slide
        self.advance_time(1)
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_6')

    def test_current_slide_transition_out(self):
        # Tests a new slide with no transition, but the current slide has one,
        # so it uses that

        # show a slide, no expire, but with transition out
        self.mc.events.post('show_slide_9')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_9')

        # show a new slide with no transition
        self.assertIsNone(self.mc.slides['machine_slide_6']['transition'])
        self.mc.events.post('machine_slide_6')
        self.advance_time()

        # transition from first slide should be happening
        self.assertTrue(isinstance(self.mc.targets['display1'].transition,
                                   MoveInTransition))

    def test_both_slides_transitions(self):
        # current slide has transition out, and new slide has transition, so
        # transition of new slide takes precendence

        # show a slide, no expire, but with transition out
        self.assertEqual(
            self.mc.slides['machine_slide_8']['transition_out']['type'],
            'wipe')
        self.mc.events.post('show_slide_8')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_8')

        # show a new slide with a different transition in
        self.assertEqual(
            self.mc.slides['machine_slide_9']['transition']['type'], 'move_in')
        self.mc.events.post('show_slide_9')
        self.advance_time()

        # transition from second slide should be happening
        self.assertTrue(isinstance(self.mc.targets['display1'].transition,
                                   MoveInTransition))

    def test_transition_in_slide_player(self):
        # transition is specified in slide player for slide that does not have
        # transition

        # show a base slide with no transition
        self.assertIsNone(self.mc.slides['machine_slide_4']['transition'])
        self.mc.events.post('machine_slide_4')
        self.advance_time()

        # show a second slide where the slide has no transition, but the
        # slide player does have a transition
        self.assertIsNone(self.mc.slides['machine_slide_5']['transition'])
        self.mc.events.post('show_slide_5_with_transition')
        self.advance_time()

        # make sure the transition is happening
        self.assertTrue(isinstance(self.mc.targets['display1'].transition,
                                   FadeTransition))

    def test_transition_in_slide_player_override(self):
        # transition in slide player for slide that already has a transition.
        # the slide player transition should override the slide one

        # show a base slide with no transition
        self.assertIsNone(self.mc.slides['machine_slide_4']['transition'])
        self.mc.events.post('machine_slide_4')
        self.advance_time()

        # show a second slide where the slide has a transition, but the
        # slide player has a different transition, so the slide player
        # should take precedence
        self.assertEqual(
            self.mc.slides['machine_slide_9']['transition']['type'], 'move_in')
        self.mc.events.post('show_slide_5_with_transition')
        self.advance_time()

        # make sure the transition from the slide player is happening
        self.assertTrue(isinstance(self.mc.targets['display1'].transition,
                                   FadeTransition))

    def test_slide_show(self):
        # tests the 'show' feature of a slide. This is not a slide show, but
        # rather a setting which controls whether a slide is shown right away
        # or not

        # show a base slide
        self.mc.events.post('show_slide_1')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')

        # post new slide, but with show=False, so it should not show
        self.mc.events.post('slide_2_dont_show')
        self.advance_time()
        # Should still be slide 1
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')

    def test_slide_removal(self):
        # Also test slide events
        self.mock_event('slide_machine_slide_1_active')
        self.mock_event('slide_machine_slide_1_created')
        self.mock_event('slide_machine_slide_1_removed')
        self.mock_event('slide_machine_slide_4_active')
        self.mock_event('slide_machine_slide_4_created')
        self.mock_event('slide_machine_slide_4_removed')

        # show a base slide
        self.mc.events.post('show_slide_1')
        self.advance_time(0.3)
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')

        self.assertEventCalled('slide_machine_slide_1_created')
        self.assertEventCalled('slide_machine_slide_1_active')
        self.assertEventNotCalled('slide_machine_slide_1_removed')
        self.assertEventNotCalled('slide_machine_slide_4_created')
        self.assertEventNotCalled('slide_machine_slide_4_active')
        self.assertEventNotCalled('slide_machine_slide_4_removed')

        # show another slide
        self.mc.events.post('show_slide_4')
        self.advance_time(0.3)
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_4')

        self.assertEventCalled('slide_machine_slide_1_created', 1)
        self.assertEventCalled('slide_machine_slide_1_active', 1)
        self.assertEventNotCalled('slide_machine_slide_1_removed')
        self.assertEventCalled('slide_machine_slide_4_created', 1)
        self.assertEventCalled('slide_machine_slide_4_active', 1)
        self.assertEventNotCalled('slide_machine_slide_4_removed')

        # make sure base slide comes back
        self.mc.events.post('remove_slide_4')
        self.advance_time(0.3)
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')

        self.assertEventCalled('slide_machine_slide_1_created', 1)
        self.assertEventCalled('slide_machine_slide_1_active', 2)
        self.assertEventNotCalled('slide_machine_slide_1_removed')
        self.assertEventCalled('slide_machine_slide_4_created', 1)
        self.assertEventCalled('slide_machine_slide_4_active', 1)
        self.assertEventCalled('slide_machine_slide_4_removed', 1)

    def test_slide_removal_new_transition(self):
        # show a base slide
        self.mc.events.post('show_slide_1')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')

        # show a slide with not transition out
        self.assertIsNone(self.mc.slides['machine_slide_4']['transition_out'])
        self.mc.events.post('show_slide_4')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_4')

        # remove that slide with a transition
        self.mc.events.post('remove_slide_4_with_transition')
        self.advance_time(.1)

        # make sure the transition is taking effect
        self.assertTrue(isinstance(self.mc.targets['display1'].transition,
                                   WipeTransition))

        # original slide is back
        self.advance_time(1)
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')

    def test_slide_removal_existing_transition(self):
        # show a base slide
        self.mc.events.post('show_slide_1')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')

        # show a slide which has a transition out
        self.assertEqual(
            self.mc.slides['machine_slide_8']['transition_out']['type'],
            'wipe')
        self.mc.events.post('show_slide_8')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_8')

        # post an event which does not have a transition
        self.mc.events.post('remove_slide_8')
        self.advance_time(.1)

        # make sure the transition is taking effect
        self.assertTrue(isinstance(self.mc.targets['display1'].transition,
                                   WipeTransition))

        # original slide is back
        self.advance_time(1)
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')

    def test_slide_removal_override_transition(self):
        # show a base slide
        self.mc.events.post('show_slide_1')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')

        # show a slide which has a wipe transition
        self.assertEqual(
            self.mc.slides['machine_slide_8']['transition_out']['type'],
            'wipe')
        self.mc.events.post('show_slide_8')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_8')

        # remove slide with a fade transition
        self.mc.events.post('remove_slide_8_fade')
        self.advance_time(.1)

        # make sure it uses the fade transition from the slide player
        self.assertTrue(isinstance(self.mc.targets['display1'].transition,
                                   FadeTransition))

        # original slide should be back
        self.advance_time(1)
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')

    def test_removing_last_slide(self):
        self.mc.events.post('show_slide_1')
        self.advance_time()
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'machine_slide_1')
        self.advance_time()
        self.mc.targets['default'].remove_slide('machine_slide_1')
        self.advance_time()
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'display1_blank')
        self.assertEqual(1, len(self.mc.targets['default'].screens))

    def test_expire_non_current_slide(self):
        self.mc.events.post('slide1_expire_1s')
        self.advance_time(.1)
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'machine_slide_1')

        # show slide 2 which should expire in 1s
        self.mc.events.post('slide2_expire_1s')
        self.advance_time(.1)
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'machine_slide_2')

        self.advance_time(1)

        # should be back to blank, because slide1 expired while slide 2 was up
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'display1_blank')
        self.assertEqual(1, len(self.mc.targets['default'].screens))

    def test_remove_already_removed_slide(self):
        self.mc.events.post('slide1_expire_1s')
        self.advance_time(.1)
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'machine_slide_1')

        # grab a reference to this slide
        slide1 = self.mc.targets['default'].current_slide

        self.advance_time(1)

        # should be blank, because slide1 expired
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'display1_blank')
        self.assertEqual(1, len(self.mc.targets['default'].screens))

        # now try to call the now-gone slide's remove

        slide1.remove()
        self.advance_time()

    def test_animation_triggers(self):
        bcp_command1 = ('register_trigger', None, {'event': 'flash_widget_1'})
        bcp_command2 = ('register_trigger', None, {'event': 'flash_widget_2'})
        self.assertNotIn(bcp_command1, self.sent_bcp_commands)
        self.assertNotIn(bcp_command2, self.sent_bcp_commands)

        self.mc.events.post("client_connected")
        self.advance_time()
        self.assertIn(bcp_command1, self.sent_bcp_commands)
        self.assertIn(bcp_command2, self.sent_bcp_commands)

    def test_play_multiple_times(self):
        # set a baseline slide
        self.mc.events.post('show_slide_1')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'machine_slide_1')

        # start the mode and then post that event again. The slide should
        # switch
        self.mc.modes['mode1'].start()

        self.mc.events.post('show_mode1_slide')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name, 'mode1_slide')
        slide = weakref.ref(self.mc.targets['display1'].current_slide)

        for i in range(10):
            self.mc.events.post('show_mode1_slide')
            self.advance_time()
            self.assertEqual(self.mc.targets['display1'].current_slide_name, 'mode1_slide')
            # run garbage collector
            gc.collect()
            # weak ref to the slide should be none
            self.assertIsNone(slide())
            # build weak ref to curent slide
            slide = weakref.ref(self.mc.targets['display1'].current_slide)

    def test_conditional_slide(self):
        self.mc.events.post('show_conditional_slide', var='foo')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'slide_condition_foo')
        self.mc.events.post('show_conditional_slide', var='bar')
        self.advance_time()
        self.assertEqual(self.mc.targets['display1'].current_slide_name,
                         'slide_condition_bar')


class TestMpfSlidePlayer(MpfTestCase):

    # runs the MPF tests (and not the MPF-MC ones) to test the MPF side of the
    # slide player plugin

    def __init__(self, methodName):
        super().__init__(methodName)
        # remove config patch which disables bcp
        del self.machine_config_patches['bcp']

    def get_absolute_machine_path(self):
        # override the base to we set the patch based on the mpfmc location
        return os.path.abspath(os.path.join(
            mpfmc.core.__path__[0], os.pardir, self.get_machine_path()))

    def get_enable_plugins(self):
        return True

    def get_config_file(self):
        return 'test_slide_player.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/slide_player/'

    # todo add tests
