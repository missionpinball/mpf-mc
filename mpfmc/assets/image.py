import os
import zipfile
from io import BytesIO

from kivy import Logger

from kivy.cache import Cache

from kivy.core.image import Image, ImageLoaderBase, ImageLoader, Texture
from mpf.core.assets import AssetPool
from mpf.core.utility_functions import Util

from mpfmc.assets.mc_asset import McAsset

# This module has extra comments since it's what we tell people to use as an
# example of an Asset implementation.


class ImagePool(AssetPool):

    """A pool of images."""

    __slots__ = []

    def __repr__(self):
        # String that's returned if someone prints this object
        return '<ImagePool: {}>'.format(self.name)

    @property
    def image(self):
        return self.asset


class LazyZipImageLoaderTexture:

    """Lazy textures for images inside a zip."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, zip_file, filename, mipmap, keep_data, no_cache):
        self._zip_file = zip_file
        self._mipmap = mipmap
        self._keep_data = keep_data
        self._no_cache = no_cache
        self._filename = filename
        znamelist = self._zip_file.namelist()
        znamelist.sort()
        self._index_list = []
        self.width = None
        self.height = None

        for zfilename in znamelist:
            if zfilename.endswith(os.sep) or zfilename.startswith("."):
                # skip directories and hidden files
                continue
            self._index_list.append(zfilename)

        self._loaded_textures = [None] * len(self._index_list)

    def __len__(self):
        return len(self._index_list)

    def __getitem__(self, item):
        if not self._loaded_textures[item]:
            # first, check if a texture with the same name already exist in the
            # cache
            # pylint: disable-msg=redefined-builtin
            chr = type(self._filename)
            uid = chr(u'%s|%d|%d') % (self._filename, self._mipmap, item)
            texture = Cache.get('kv.texture', uid)

            # if not create it and append to the cache
            if texture is None:
                zfilename = self._index_list[item]
                # read file and store it in mem with fileIO struct around it
                tmpfile = BytesIO(self._zip_file.read(zfilename))
                ext = zfilename.split('.')[-1].lower()
                image = None
                for loader in ImageLoader.loaders:
                    if (ext not in loader.extensions() or
                            not loader.can_load_memory()):
                        continue
                    Logger.debug('Image%s: Load <%s> from <%s>',
                                 loader.__name__[11:], zfilename,
                                 self._filename)
                    try:
                        image = loader(zfilename, ext=ext, rawdata=tmpfile,
                                       inline=True)
                    except:     # pylint: disable-msg=bare-except   # noqa
                        # Loader failed, continue trying.
                        continue
                    break
                if image is None:
                    raise AssertionError("Could not load image {} (index {}) "
                                         "from zip {}".format(zfilename, item,
                                                              self._filename))

                self.width = image.width
                self.height = image.height

                imagedata = image._data[0]  # pylint: disable-msg=protected-access

                source = '{}{}|'.format(
                    'zip|' if self._filename.endswith('.zip') else '',
                    self._no_cache)
                imagedata.source = chr(source) + uid
                texture = Texture.create_from_data(
                    imagedata, mipmap=self._mipmap)
                if not self._no_cache:
                    Cache.append('kv.texture', uid, texture)
                if imagedata.flip_vertical:
                    texture.flip_vertical()

            self._loaded_textures[item] = texture

        return self._loaded_textures[item]


class LazyZipImageLoader(ImageLoaderBase):

    """Lazy image loader for image inside a zip."""

    @staticmethod
    def save(*largs, **kwargs):
        raise AssertionError("Not supported")

    def __init__(self, filename, zip_file, **kwargs):
        super().__init__(filename, **kwargs)
        self._zipfile = zip_file
        self._data = dict()     # to prevent breakage in loader::_load_urllib
        self._textures = None

    def load(self, filename):
        """Return the zip object."""
        return filename

    def populate(self):
        """Populate textures with lazy loader."""
        if not self._textures:
            self._textures = LazyZipImageLoaderTexture(self._zipfile,
                                                       self.filename,
                                                       self._mipmap,
                                                       self.keep_data,
                                                       self._nocache)

    @property
    def width(self):
        '''Image width
        '''
        if not self._textures:
            self.populate()
        return self._textures.width

    @property
    def height(self):
        '''Image height
        '''
        if not self._textures:
            self.populate()
        return self._textures.height

    @property
    def size(self):
        '''Image size (width, height)
        '''
        return (self.width, self.height)


class KivyImageLoaderPatch:

    """Patch Kivy zip loader."""

    @staticmethod
    def lazy_zip_loader(filename):
        '''Read images from an zip file lazily.

        .. versionadded:: 1.12.0

        Returns an LazyZipImageLoader which loads images from a zip on demand.
        '''
        # read zip in memory for faster access
        with open(filename, 'rb') as handle:
            _file = BytesIO(handle.read())
        # read all images inside the zip
        zip_file = zipfile.ZipFile(_file)

        return LazyZipImageLoader(filename, zip_file=zip_file, inline=True)


class ImageAsset(McAsset):

    attribute = 'images'  # attribute in MC, e.g. self.mc.images
    path_string = 'images'  # entry from mpf-mc:paths: for asset folder name
    config_section = 'images'  # section in the config files for this asset
    extensions = ('png', 'jpg', 'jpeg', 'gif', 'zip', 'bmp')  # obvious. No dots.
    class_priority = 100  # Order asset classes are loaded. Higher is first.
    pool_config_section = 'image_pools'  # Will setup groups if present
    asset_group_class = ImagePool  # Class or None to not use pools

    __slots__ = ["frame_persist", "frame_skips", "references", "_image"]

    def __init__(self, mc, name, file, config):
        super().__init__(mc, name, file, config)  # be sure to call super

        # Do whatever else you want here. You can remove the entire method if
        # you don't need to do anything.

        self._image = None  # holds the actual image in memory
        self.frame_persist = None
        self.frame_skips = None
        self.references = 0

    @property
    def image(self):
        # Since self._image will change depending on whether the image is
        # loaded or not, set a property so external methods can just use
        # ImageAsset.image

        return self._image

    def do_load(self):
        """Load the image."""
        # This is the method that's actually called to load the asset from
        # disk. It's called by the loader thread so it's ok to block. However
        # since it's a separate thread, don't update any other attributes.

        # When you're done loading and return, the asset will be processed and
        # the various load status attributes will be updated automatically,
        # and anything that was waiting for it to load will be called. So
        # all you have to do here is load and return.

        if self.config.get('image_template'):
            try:
                template = self.machine.machine_config['image_templates'][self.config['image_template']]
                self.config = Util.dict_merge(template, self.config)
            except KeyError:
                raise KeyError("Image template '{}' was not found, referenced in image config {}".format(
                               self.config['image_template'], self.config))

        if self.machine.machine_config['mpf-mc']['zip_lazy_loading']:
            # lazy loading for zip file image sequences
            ImageLoader.zip_loader = KivyImageLoaderPatch.lazy_zip_loader

        self._image = Image(self.config['file'],
                            keep_data=False,
                            scale=1.0,
                            mipmap=False,
                            anim_delay=-1,
                            nocache=True)

        self._image.anim_reset(False)

        if self.config.get('frame_skips'):
            # Frames are provided in 1-index values, but the image animates in zero-index values
            self.frame_skips = {s['from'] - 1: s['to'] - 1 for s in self.config['frame_skips']}

        # load first texture to speed up first display
        self._callbacks.add(lambda x: self._image.texture)

    def _do_unload(self):
        # This is the method that's called to unload the asset. It's called by
        # the main thread so you don't have to worry about thread
        # complexities, but since it's in the main thread, you need to
        # return quickly.

        self._image = None
