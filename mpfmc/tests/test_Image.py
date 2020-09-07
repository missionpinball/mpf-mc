# Tests the Image Asset and the Image widget


from mpfmc.tests.MpfMcTestCase import MpfMcTestCase
from mpfmc.tests.MpfSlideTestCase import MpfSlideTestCase


class TestImage(MpfMcTestCase, MpfSlideTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/assets_and_image'

    def get_config_file(self):
        return 'test_image.yaml'

    def test_image(self):
        self.mc.events.post('show_slide1')

        # This tests includes images that preload and that load on demand, so
        # give it enough time to for the on demand ones to load
        self.advance_time()

        # Make sure that all the images are showing.
        active_widget_names = [
            x.widget.image.name for x in self.mc.targets['default'].current_slide.widgets]

        for x in range(12):
            self.assertIn('image{}'.format(x+1), active_widget_names)

    def test_image_pools(self):
        self.mc.events.post("show_random_slide")
        self.advance_time(.1)
        self.assertSlideOnTop("random_image_test")
        self.mc.events.post("add_random_image")
        self.advance_time(.1)
        self.mc.events.post("remove_random_image")
        self.advance_time(.1)
