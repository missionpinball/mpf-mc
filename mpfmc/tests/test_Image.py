# Tests the Image Asset and the Image widget


from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestImage(MpfMcTestCase):
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
