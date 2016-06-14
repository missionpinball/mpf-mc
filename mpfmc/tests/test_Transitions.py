from mpfmc.tests.MpfMcTestCase import MpfMcTestCase
from mpfmc.transitions.push import PushTransition
from kivy.uix.screenmanager import WipeTransition, NoTransition


class TestTransitions(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/transitions'

    def get_config_file(self):
        return 'test_transitions.yaml'

    def test_transition_loading(self):
        # test that the mpf transitions have loaded
        self.assertIn('push', self.mc.transition_manager.transitions)
        self.assertEqual(self.mc.transition_manager.transitions['push'],
                         PushTransition)

        # test that the kivy transitions have loaded
        self.assertIn('wipe', self.mc.transition_manager.transitions)
        self.assertEqual(self.mc.transition_manager.transitions['wipe'],
                         WipeTransition)

    def test_mpf_transition(self):
        self.mc.events.post('show_slide1')

        # show a slide with a transition
        self.mc.events.post('show_slide2')
        self.advance_time(1)

        # transition is 2 secs, so we can check the progress here
        slide = self.mc.targets['default'].current_slide

        self.assertAlmostEqual(slide.transition_progress, 0.5, delta=.1)
        self.assertEqual(slide.transition_state,'in')

        transition = self.mc.targets['default'].transition
        self.assertEqual(transition.duration, 2.0)
        self.assertTrue(transition.is_active)
        self.assertEqual(transition.easing, 'out_bounce')
        self.assertTrue(isinstance(transition, PushTransition))

    def test_target_transition_reset_when_done(self):
        # Show slide1 with no transition
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.assertTrue(isinstance(self.mc.targets['default'].transition,
                                   NoTransition))
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        # Show slide2 with a transition
        self.mc.events.post('push_left')
        self.advance_time()
        self.assertTrue(isinstance(self.mc.targets['default'].transition,
                                   PushTransition))
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide2')

        # Go back to slide1 with a transition
        self.mc.events.post('show_slide1_with_push')
        self.advance_time()
        self.assertTrue(isinstance(self.mc.targets['default'].transition,
                                   PushTransition))
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('push_left')
        self.advance_time()
        self.assertTrue(isinstance(self.mc.targets['default'].transition,
                                   PushTransition))
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide2')

        self.mc.events.post('show_slide1')
        self.advance_time()
        self.assertTrue(isinstance(self.mc.targets['default'].transition,
                                   NoTransition))
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide1')

        self.mc.events.post('show_slide2_no_transition')
        self.advance_time()
        self.assertTrue(isinstance(self.mc.targets['default'].transition,
                                   NoTransition))
        self.assertEqual(self.mc.targets['default'].current_slide_name,
                         'slide2')

    def test_push_left(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('push_left')
        self.advance_time()

    def test_push_right(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('push_right')
        self.advance_time()

    def test_push_up(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('push_up')
        self.advance_time()

    def test_push_down(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('push_down')
        self.advance_time()

    def test_move_in_right(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('move_in_right')
        self.advance_time()

    def test_move_in_left(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('move_in_left')
        self.advance_time()

    def test_move_in_top(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('move_in_top')
        self.advance_time()

    def test_move_in_bottom(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('move_in_bottom')
        self.advance_time()

    def test_move_out_right(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('move_out_right')
        self.advance_time()

    def test_move_out_left(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('move_out_left')
        self.advance_time()

    def test_move_out_top(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('move_out_top')
        self.advance_time()

    def test_move_out_bottom(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('move_out_bottom')
        self.advance_time()

    def test_wipe(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('wipe')
        self.advance_time()

    def test_swap(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('swap')
        self.advance_time()

    def test_fade(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('fade')
        self.advance_time()

    def test_fade_back(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('fade_back')
        self.advance_time()

    def test_rise_in(self):
        self.mc.events.post('show_slide1')
        self.advance_time()
        self.mc.events.post('rise_in')
        self.advance_time()

    # def test_no_transition_1(self):
    #     self.mc.events.post('show_slide1')
    #     self.advance_time()
    #     self.mc.events.post('no_transition_1')
    #     self.advance_time(.5)
    #
    # def test_no_transition_2(self):
    #     self.mc.events.post('show_slide1')
    #     self.advance_time()
    #     self.mc.events.post('no_transition_2')
    #     self.advance_time(.5)
    #
    # def test_no_transition_3(self):
    #     self.mc.events.post('show_slide1')
    #     self.advance_time()
    #     self.mc.events.post('no_transition_3')
    #     self.advance_time(.5)
