
from tests.MpfMcTestCase import MpfMcTestCase


class TestVideo(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/video'

    def get_config_file(self):
        return 'test_video.yaml'

    def _test_video(self):

        self.assertIn('mpf_video_small_test', self.mc.videos)
        self.mc.events.post('show_slide1')
        self.advance_time()

        self.advance_time(1)

        video_wid = self.mc.targets['default'].current_slide.children[0]
