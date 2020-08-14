from mpfmc.tests.MpfIntegrationTestCase import MpfIntegrationTestCase
from mpfmc.tests.MpfSlideTestCase import MpfSlideTestCase
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestWidgetsAndSlides(MpfIntegrationTestCase, MpfFakeGameTestCase, MpfSlideTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'integration/machine_files/widgets_and_slides/'

    def test_animation_events(self):
        self.post_event("play_animation_show")
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide("Test Text")
        self.assertEqual(0.0, self.mc.targets["default"].current_slide.children[0].widget.rotate.angle)
        self.post_event("event_to_rotate_widget")
        self.advance_time_and_run(.1)
        self.assertEqual(90.0, self.mc.targets["default"].current_slide.children[0].widget.rotate.angle)

    def test_slide_with_vars(self):
        self.post_event("play_show_with_var")
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide("SLIDE WITH VAR Test123")

    def test_anonymous_slides(self):
        self.post_event("start_mode1")
        self.advance_time_and_run(.1)
        self.post_event("show_anonymous_slide1")
        self.advance_time_and_run(.1)

        # anonymous slide1 is on top (mode1)
        self.assertTextOnTopSlide("Anonymous Slide1")
        self.assertSlideOnTop("mode1.slide_player-show_anonymous_slide1")

        self.post_event("start_mode2")
        self.advance_time_and_run(.1)
        self.post_event("show_anonymous_slide2")
        self.advance_time_and_run(.1)

        # anonymous slide2 is on top (mode2)
        self.assertTextOnTopSlide("Anonymous Slide2")
        self.assertSlideOnTop("mode2.slide_player-show_anonymous_slide2")

        self.post_event("stop_mode2")
        self.advance_time_and_run(.1)

        # anonymous slide1 is on top again (mode1)
        self.assertTextOnTopSlide("Anonymous Slide1")
        self.assertSlideOnTop("mode1.slide_player-show_anonymous_slide1")

    def test_upper_case_mode(self):
        """This used to crash."""
        self.start_mode("Upper_Case_Mode")
        self.post_event("show_random_slide")
        self.advance_time_and_run(.1)
        self.assertSlideOnTop("random_slide")
        self.stop_mode("Upper_Case_Mode")
        self.advance_time_and_run(.1)

    def test_mode_start_from_mc(self):
        self.start_game()
        self.mc.post_mc_native_event("start_mode6")
        self.advance_time_and_run()
        self.assertModeRunning("mode6")
        self.assertTextOnTopSlide('Slide Mode 6')

    def test_condition_slide_player(self):
        self.start_game()
        self.mc.post_mc_native_event("start_mode7")
        self.advance_time_and_run()
        self.assertModeRunning("mode7")
        self.post_event_with_params("test_conditional", var=1)
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide('Condition 1')
        self.post_event("remove_conditional")
        self.post_event_with_params("test_conditional", var=2)
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide('Condition 2')

    def test_placeholders(self):
        self.post_event("play_slide_last_game_score")
        self.advance_time_and_run(.1)
        self.assertTextInSlide('Player1:  Player2: ', "slide_last_game_score")

        self.start_game()
        self.add_player()
        self.post_event("start_mode4")
        self.advance_time_and_run(.1)
        self.post_event("show_variable_slide")
        self.machine.variables.set_machine_var("test1", "asd")
        self.advance_time_and_run(.1)
        self.assertSlideOnTop("variable_slide")
        self.assertTextInSlide('MAIN TEXT 1:Test 2:7 3:1.75 4:asd', "variable_slide")
        self.machine.game.player["test_int"] = 42
        self.machine.game.player["test_float"] = 42.23
        self.machine.game.player["test_str"] = "1337"
        self.machine.game.player["score"] = 1337
        self.machine.variables.set_machine_var("test1", "l33t")
        self.advance_time_and_run(.1)
        self.assertTextInSlide('MAIN TEXT 1:1337 2:42 3:42.23 4:l33t', "variable_slide")
        self.drain_all_balls()
        self.advance_time_and_run(.1)
        self.machine.game.player["score"] = 42
        self.post_event("start_mode4")
        self.advance_time_and_run(.1)
        self.post_event("show_variable_slide")
        self.advance_time_and_run(.1)
        self.assertTextInSlide('MAIN TEXT 1:Test 2:7 3:1.75 4:l33t', "variable_slide")
        self.stop_game()
        self.advance_time_and_run(.1)

        self.post_event("play_slide_last_game_score")
        self.advance_time_and_run(.1)
        self.assertTextInSlide('Player1: 1337 Player2: 42', "slide_last_game_score")

        self.start_game()
        self.advance_time_and_run(.1)
        self.machine.game.player["score"] = 23
        self.advance_time_and_run(.1)
        self.stop_game()

        self.post_event("play_slide_last_game_score")
        self.advance_time_and_run(.1)
        self.assertTextInSlide('Player1: 23 Player2: ', "slide_last_game_score")

    def test_widget_on_slide_of_another_mode(self):
        self.post_event("start_mode1")
        self.advance_time_and_run()
        self.post_event("show_widget_mode1_on_slide_mode2")
        self.advance_time_and_run()

        self.assertSlideNotActive("slide_mode2")

        self.post_event("start_mode2")
        self.advance_time_and_run()
        self.post_event("show_slide_mode2")
        self.advance_time_and_run()

        self.assertSlideOnTop("slide_mode2")
        self.assertTextInSlide("Widget Mode 1", "slide_mode2")

    def test_slide_on_target_of_another_mode(self):
        self.post_event("start_mode1")
        self.advance_time_and_run()
        self.post_event("play_slide_mode1_on_frame_mode2")
        self.advance_time_and_run()

        self.assertTextNotOnTopSlide("Slide Mode 1")

        self.post_event("start_mode2")
        self.advance_time_and_run()
        self.post_event("show_slide_mode2_frame")
        self.advance_time_and_run()

        self.assertSlideOnTop("slide_mode2_frame")
        self.assertTextInSlide("Slide Mode 1", "slide_mode2_frame")
        self.assertTextOnTopSlide("Slide Mode 1")

        # remove slide frame
        self.post_event("remove_slide_mode2_frame")
        self.advance_time_and_run()

        self.assertTextNotOnTopSlide("Slide Mode 1")

        # add again
        self.post_event("show_slide_mode2_frame")
        self.advance_time_and_run()

        # text should be there again
        self.assertTextOnTopSlide("Slide Mode 1")

        self.post_event("remove_slide_mode1_on_frame_mode2")
        self.advance_time_and_run()

        # text should not be there
        self.assertTextNotOnTopSlide("Slide Mode 1")

        # add text
        self.post_event("play_slide_mode1_on_frame_mode2")
        self.advance_time_and_run()

        # text should be there again
        self.assertTextOnTopSlide("Slide Mode 1")

        # remove slide frame
        self.post_event("remove_slide_mode2_frame")
        self.advance_time_and_run()

        # add again
        self.post_event("show_slide_mode2_frame")
        self.advance_time_and_run()

        # text should be there again
        self.assertTextOnTopSlide("Slide Mode 1")

        # remove slide frame
        self.post_event("remove_slide_mode2_frame")
        self.advance_time_and_run()

        self.post_event("remove_slide_mode1_on_frame_mode2")
        self.advance_time_and_run()

        # add again
        self.post_event("show_slide_mode2_frame")
        self.advance_time_and_run()

        # text should not be there
        self.assertTextNotOnTopSlide("Slide Mode 1")

    def test_moving_slide_frame(self):
        self.post_event("start_mode3")
        self.advance_time_and_run()
        self.assertModeRunning("mode3")

        self.post_event("show_top_slide")
        self.advance_time_and_run()
        self.post_event("show_content_slide")
        self.advance_time_and_run()

        self.assertTextOnTopSlide("ASD")
        self.assertTextOnTopSlide("ASD2")

        self.assertAlmostEqual(16, self.mc.active_slides['top_slide'].widgets[0].widget.y)

        self.post_event("move_out")
        self.advance_time_and_run()
        self.assertAlmostEqual(-100.0, self.mc.active_slides['top_slide'].widgets[0].widget.y)
        self.post_event("move_back")
        self.advance_time_and_run()

        self.assertAlmostEqual(-134.0, self.mc.active_slides['top_slide'].widgets[0].widget.y)

    def test_dynamic_widget_width(self):
        self.start_game()
        self.start_mode("mode5")
        self.post_event("show_green_slide")
        self.advance_time_and_run(.1)
        self.assertEqual(0, self.mc.active_slides['green_slide'].widgets[0].widget.width)
        self.machine.game.player.greenness = 30
        self.advance_time_and_run(1.1)
        self.assertEqual(30, self.mc.active_slides['green_slide'].widgets[0].widget.width)
        self.machine.game.player.greenness = 100
        self.advance_time_and_run(1.1)
        self.assertEqual(100, self.mc.active_slides['green_slide'].widgets[0].widget.width)

