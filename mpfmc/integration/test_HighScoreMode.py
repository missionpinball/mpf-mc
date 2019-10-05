"""Test high score mode."""
from collections import OrderedDict
import time

from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase

from mpfmc.tests.MpfSlideTestCase import MpfSlideTestCase

from mpfmc.tests.MpfIntegrationTestCase import MpfIntegrationTestCase


class TestHighScoreMode(MpfIntegrationTestCase, MpfSlideTestCase, MpfFakeGameTestCase):

    def get_config_file(self):
        return 'high_score.yaml'

    def get_machine_path(self):
        return 'integration/machine_files/high_score/'

    def test_empty_name(self):
        self.start_game()
        self.machine.game.player_list[0].score = 10000
        self.machine.game.player_list[0].loops = 100
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes.high_score.active)
        self.hit_and_release_switch("s_left_flipper")
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide("PLAYER 1")
        self.assertTextOnTopSlide("GRAND CHAMPION")
        self.assertTextOnTopSlide("END")
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run(.5)
        self.assertTextOnTopSlide("GRAND CHAMPION")
        self.assertTextOnTopSlide("")
        self.advance_time_and_run(5)
        self.assertTextOnTopSlide("LOOP CHAMP")
        self.assertTextOnTopSlide("")

    def test_no_high_scores(self):
        self.start_game()
        self.machine.game.player_list[0].score = 10000
        self.machine.game.player_list[0].loops = 100
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes.high_score.active)

        self.assertTextOnTopSlide("PLAYER 1")
        self.assertTextOnTopSlide("GRAND CHAMPION")
        self.assertTextOnTopSlide("A")

        for i in range(9):
            self.hit_and_release_switch("s_right_flipper")
        self.advance_time_and_run()
        self.assertTextOnTopSlide("J")

        self.hit_and_release_switch("s_start")
        for i in range(9):
            self.hit_and_release_switch("s_left_flipper")
        self.advance_time_and_run()
        self.assertTextOnTopSlide("A")

        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()

        self.assertTextOnTopSlide("JA")

        self.hit_and_release_switch("s_right_flipper")
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()

        self.assertTextOnTopSlide("JAB")

        self.hit_and_release_switch("s_start")
        self.advance_time_and_run(.5)
        self.assertTextOnTopSlide("GRAND CHAMPION")
        self.assertTextOnTopSlide("JAB")
        self.advance_time_and_run(5)
        self.assertTextOnTopSlide("LOOP CHAMP")
        self.assertTextOnTopSlide("JAB")
        self.advance_time_and_run(5)

        self.assertFalse(self.machine.modes.high_score.active)
