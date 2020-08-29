from mpfmc.tests.MpfIntegrationTestCase import MpfIntegrationTestCase
from mpfmc.tests.MpfSlideTestCase import MpfSlideTestCase


class TestService(MpfIntegrationTestCase, MpfSlideTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'integration/machine_files/service_mode/'

    def test_service_slides(self):
        # open door
        self.hit_switch_and_run("s_door_open", 1)
        self.assertModeRunning("attract")
        self.assertSlideOnTop("service_door_open")
        self.assertTextOnTopSlide("Coil Power Off")

        # enter
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run(.1)
        self.assertSlideOnTop("service_menu")
        self.assertTextOnTopSlide("Diagnostics Menu")

        # enter diagnostics menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide("Switch Menu")

        # enter switch menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide("Switch Edge Test")

        # enter switch test
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run(.1)
        self.assertSlideOnTop("service_switch_test")

        self.hit_and_release_switch("s_test")
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide("s_test")
        self.assertTextOnTopSlide("The test switch label")

        # exit
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run(.1)
        self.assertSlideOnTop("service_menu")
        self.assertTextOnTopSlide("Switch Edge Test")

        # exit
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run(.1)
        self.assertSlideOnTop("service_menu")
        self.assertTextOnTopSlide("Switch Menu")

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide("Coil Menu")

        # enter coil menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide("Single Coil Test")

        # enter coil test
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run(.1)
        self.assertSlideOnTop("service_coil_test")
        self.assertTextOnTopSlide("c_test")
        self.assertTextOnTopSlide("First coil")
        self.assertTextOnTopSlide("Coil Power Off")

        # exit
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run(.1)
        self.assertSlideOnTop("service_menu")
        self.assertTextOnTopSlide("Single Coil Test")

        # exit
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run(.1)
        self.assertSlideOnTop("service_menu")
        self.assertTextOnTopSlide("Coil Menu")

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide("Light Menu")

        # enter light menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide("Single Light Test")

        # enter light test
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run(.1)
        self.assertSlideOnTop("service_light_test")
        self.assertTextOnTopSlide("l_light1")
        self.assertTextOnTopSlide("First light")
        self.assertTextOnTopSlide("1/white")

        # exit
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run(.1)
        self.assertSlideOnTop("service_menu")
        self.assertTextOnTopSlide("Single Light Test")

        # exit
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run(.1)
        self.assertSlideOnTop("service_menu")
        self.assertTextOnTopSlide("Light Menu")

        # exit
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run(.1)
        self.assertSlideOnTop("service_menu")
        self.assertTextOnTopSlide("Diagnostics Menu")

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide("Audits Menu")

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide("Adjustments Menu")

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide("Utilities Menu")

        # enter util menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide("Reset Menu")

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run(.1)
        self.assertTextOnTopSlide("Software Update")

        # close door
        self.release_switch_and_run("s_door_open", 1)
        self.assertTextNotOnTopSlide("Coil Power Off")

        # exit
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run(.1)
        self.assertSlideOnTop("service_menu")

        # exit service menu
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run(.1)

        if not self.mc.sound_system or not self.mc.sound_system.audio_interface:
            return

        # test volume
        self.assertEqual(0.8, self.machine.variables.get_machine_var("master_volume"))

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run(.1)
        self.assertEqual(0.84, self.machine.variables.get_machine_var("master_volume"))
