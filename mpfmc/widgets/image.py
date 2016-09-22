from kivy.uix.image import Image

from mpfmc.uix.widget import MpfWidget


class ImageWidget(MpfWidget, Image):
    widget_type_name = 'Image'
    merge_settings = ('height', 'width')

    def __init__(self, mc, config, key=None, **kwargs):
        super().__init__(mc=mc, config=config, key=key)

        try:
            self.image = self.mc.images[self.config['image']]
        except:
            raise ValueError("Cannot add Image widget. Image '{}' is not a "
                             "valid image name.".format(self.config['image']))

        # Updates the config for this widget to pull in any defaults that were
        # in the asset config
        self.merge_asset_config(self.image)

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
        del args
        self.texture = self.image.image.texture
        self.size = self.texture_size  # will re-position automatically

        self._coreimage = self.image.image
        self._coreimage.bind(on_texture=self._on_tex_change)

        if self._coreimage.anim_available:
            self.fps = self.config['fps']
            self.loops = self.config['loops']
            if self.config['auto_play']:
                self.play()
            else:
                self.stop()

    def texture_update(self, *largs):
        # overrides base method to pull the texture from our ImageClass instead
        # of from a file
        del largs

        if not self.image.image:
            return

        self._loops = 0

        if self._coreimage is not None:
            self._coreimage.unbind(on_texture=self._on_tex_change)

        self._coreimage = ci = self.image.image

        ci.bind(on_texture=self._on_tex_change)
        self.texture = ci.texture

    @property
    def fps(self):
        if self._coreimage.anim_available:
            return 1 / self._coreimage.anim_delay
        else:
            return None

    @fps.setter
    def fps(self, value):
        self._coreimage.anim_delay = 1 / value

    # for some reason setting the @property here didn't work with the getter,
    # it simply wasn't called and I have no idea why. So I just setup a classic
    # style getter/setter below these two methods.
    def _get_current_frame(self):
        return self._coreimage._anim_index + 1

    def _set_current_frame(self, value):
        frame = (int(value) - 1) % len(self._coreimage.image.textures)
        if frame == self._coreimage._anim_index:
            return
        else:
            self._coreimage._anim_index = frame
            self._coreimage._texture = (
                self._coreimage.image.textures[self._coreimage._anim_index])
            self._coreimage.dispatch('on_texture')

    current_frame = property(_get_current_frame, _set_current_frame)

    @property
    def loops(self):
        return self._coreimage.anim_loop

    @loops.setter
    def loops(self, value):
        self._coreimage.anim_loop = value

    def play(self, start_frame=None):

        if start_frame:
            self._set_current_frame(start_frame)

        self._coreimage.anim_reset(True)

    def stop(self):
        self._coreimage.anim_reset(False)
