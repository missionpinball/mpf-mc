import random

from kivy.core.image import Image
from mc.core.assets import Asset, AssetGroup


# This module has extra comments since it's what we tell people to use as an
# example of an Asset implementation.

class ImageGroup(AssetGroup):

    def __repr__(self):
        # String that's returned if someone prints this object
        return '<ImageGroup: {}>'.format(self.name)

    @property
    def image(self):
        return self.asset

class ImageAsset(Asset):

    attribute='images'  # attribute in MC, e.g. self.mc.images
    path_string='images'  # entry from mpf_mc:paths: for asset folder name
    config_section='images'  # section in the config files for this asset
    extensions=('png', 'jpg', 'jpeg')  # pretty obvious. No dots.
    class_priority=100  # Order asset classes will be loaded. Higher is first.
    group_config_section='image_groups'  # Will setup groups if present
    asset_group_class=ImageGroup

    def __init__(self, mc, name, file, config):
        super().__init__(mc, name, file, config)  # be sure to call super

        # Do whatever else you want here. You can remove the entire method if
        # you don't need to do anything.

        self._image = None  # holds the actual image in memory

    def __repr__(self):
        # String that's returned if someone prints this object
        return '<Image: {}>'.format(self.name)

    @property
    def image(self):
        # Since self._image will change depending on whether the image is
        # loaded or not, set a property so external methods can just use
        # ImageAsset.image

        return self._image

    def _do_load(self):
        # This is the method that's actually called to load the asset from
        # disk. It's called by the loader thread so it's ok to block. However
        # since it's a separate thread, don't update any other attributes.

        # When you're done loading and return, the asset will be processed and
        # the various load status attributes will be updated automatically,
        # and anything that was waiting for it to load will be called. So
        # all you have to do here is load and return.

        self._image = Image.load(filename=self.config['file'],
                                 keep_data=False,
                                 scale=1.0,
                                 mipmap=False,
                                 anim_delay=0.25,
                                 nocache=True)

    def _do_unload(self):
        # This is the method that's called to unload the asset. It's called by
        # the main thread so you don't have to worry about thread
        # complexities, but since it's in the main thread, you need to
        # return quickly.

        self._image = None
