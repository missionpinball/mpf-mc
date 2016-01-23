from kivy.core.image import Image
from mc.core.assets import AssetClass

class ImageAsset(AssetClass):

    attribute='images'  # attribute in MC, e.g. self.mc.images
    path_string='images'  # entry from mpf_mc:paths: for asset folder name
    config_section='images'  # section in the config files for this asset
    extensions=('png', 'jpg', 'jpeg', 'bmp', 'dmd', 'gif')
    class_priority=100  # Order asset classes will be loaded. Higher is first.

    def __init__(self, mc, name, file, config):
        super().__init__(mc, name, file, config)

        # do whatever else you want here. Remove the entire method if you
        # don't need to do anything.

        self.image = None  # holds the actual image in memory

    def __repr__(self):
        # String that's returned if someone prints this object
        return '<Image: {}>'.format(self.name)

    def _do_load(self):
        # This is the method that's actually called to load the asset from
        # disk. It's called by the loader thread so it's ok to block. However
        # since it is a separate thread, don't update any other attributes.

        # When you're done loading and return, the asset will be processed and
        # the ready loaded attribute will be updated automatically,
        # and anything that was waiting for it to load will be called.

        pass

    def _do_unload(self):
        # This is the method that's called to unload the asset. It's called by
        # the main thread so go nuts, but don't block since it's in the main
        # thread.

        pass

