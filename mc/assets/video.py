from kivy.core.video import Video
from mc.core.assets import Asset, AssetPool

class VideoPool(AssetPool):

    def __repr__(self):
        # String that's returned if someone prints this object
        return '<VideoPool: {}>'.format(self.name)

    @property
    def video(self):
        return self.asset

class VideoAsset(Asset):

    attribute='videos'
    path_string='videos'
    config_section='videos'
    extensions=('mkv', 'avi', 'mpg', 'mp4')
    class_priority=100
    pool_config_section='video_pools'
    asset_group_class=VideoPool

    def __init__(self, mc, name, file, config):
        super().__init__(mc, name, file, config)

        self._video = None

    def __repr__(self):
        return '<Video: {}>'.format(self.name)

    @property
    def video(self):
        return self._video

    def _do_load(self):
        self._video = Video(filename=self.config['file'])

    def _do_unload(self):
        if self._video:
            self._video.stop()
            self._video.unload()
            self._video = None
