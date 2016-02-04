from tests.MpfMcTestCase import MpfMcTestCase


class TestAnimatedImages(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/animated_images'

    def get_config_file(self):
        return 'test_animated_images.yaml'

    def test_animated_images_loading(self):
        self.assertIn('ball', self.mc.images)
        self.mc.events.post('slide1')

        self.advance_time(2)

