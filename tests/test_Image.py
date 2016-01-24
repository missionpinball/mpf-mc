# Tests the Image AssetClass and the Image widget


from tests.MpfMcTestCase import MpfMcTestCase


class TestImage(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/assets_and_image'

    def get_config_file(self):
        return 'test_image.yaml'

    def test_image(self):
        self.advance_time()
        self.mc.events.post('show_slide1')

        # This tests includes images that preload and that load on demand, so
        # give it enough time to for the on demand ones to load
        self.advance_time(2)

        # Now check a sample pixel from the screen where each image should be
        # to make sure they're really there.

        # window is 800x600, display is 400x300, so we have to double each val
        self.assertEqual(b'\xed\xd3\x01', self.get_pixel_color(100, 300))
        self.assertEqual(b'\xfe\xc7\x0f', self.get_pixel_color(160, 300))
        self.assertEqual(b'\xfb\xca\x00', self.get_pixel_color(220, 300))
        self.assertEqual(b'\xf0\xd2\x0c', self.get_pixel_color(280, 300))
        self.assertEqual(b'\xf1\xcb\x0c', self.get_pixel_color(340, 300))
        self.assertEqual(b'\xf6\xca\x0c', self.get_pixel_color(400, 300))
        self.assertEqual(b'\xf8\xd2\x0c', self.get_pixel_color(460, 300))
        self.assertEqual(b'\xed\xd3\x01', self.get_pixel_color(520, 300))
        self.assertEqual(b'\xfe\xc7\x0f', self.get_pixel_color(580, 300))
        self.assertEqual(b'\xfb\xca\x00', self.get_pixel_color(640, 300))
        self.assertEqual(b'\xed\xd3\x01', self.get_pixel_color(700, 300))
        self.assertEqual(b'\xfb\xca\x00', self.get_pixel_color(760, 300))
