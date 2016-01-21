from tests.MpfMcTestCase import MpfMcTestCase
import sys

class TestDemo(MpfMcTestCase):
    def get_machine_path(self):
        return 'examples/demo'

    def get_config_file(self):
        return 'config.yaml'

    def test_demo(self):
        # make sure it doesn't go negative
        self.mc.demo_driver.prev_slide()

        for x in range(self.mc.demo_driver.total_slides):
            self.mc.demo_driver.next_slide()
            self.advance_time()

        self.mc.demo_driver.prev_slide()

        self.assertEqual(self.mc.demo_driver.current_slide_index,
                         self.mc.demo_driver.total_slides - 1)
