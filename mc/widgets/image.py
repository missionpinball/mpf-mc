from kivy.uix.image import Image

from mc.uix.widget import MpfWidget


class ImageWidget(MpfWidget, Image):
    widget_type_name = 'Image'
    merge_settings = ('height', 'width')

    def __init__(self, mc, config, slide, mode=None, priority=None):
        super().__init__(mc=mc, mode=mode, priority=priority, slide=slide,
                         config=config)

        try:
            self.image = self.mc.images[self.config['image']]
        except:
            raise ValueError("Cannot add Image widget. Image '{}' is not a "
                             "valid image name.".format(self.config['image']))

        # Updates the config for this widget to pull in any defaults that were
        # in the asset config
        self.config = self.get_merged_asset_config(self.image)

        # If the associated image asset exists, that means it's loaded already.
        if self.image.image:
            self._image_loaded()
        else:
            # if the image asset isn't loaded, we set the size to 0,0 so it
            # doesn't show up on the display yet.
            # TODO Add log about loading on demand
            self.size = (0, 0)
            self.image.load(callback=self._image_loaded)

    def __repr__(self):  # pragma: no cover
        try:
            return '<Image name={}, size={}, pos={}>'.format(self.image.name,
                                                             self.size,
                                                             self.pos)
        except AttributeError:
            return '<Image (loading...), size={}, pos={}>'.format(self.size,
                                                                  self.pos)

    def _image_loaded(self, *args):
        self.texture = self.image.image.texture
        self.size = self.texture_size  # will re-position automatically

    def texture_update(self, *largs):
        # overrides base method to pull the texture from our ImageClass instead
        # of from a file
        if not self.image.image:
            return

        self._loops = 0

        if self._coreimage is not None:
            self._coreimage.unbind(on_texture=self._on_tex_change)

        self._coreimage = ci = self.image.image

        ci.bind(on_texture=self._on_tex_change)
        self.texture = ci.texture
