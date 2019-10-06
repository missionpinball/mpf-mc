"""Widget showing an image."""
from typing import Optional, Union

from kivy.properties import ObjectProperty, NumericProperty, AliasProperty
from kivy.graphics import Rectangle, Color, Rotate, Scale

from mpfmc.uix.widget import Widget

MYPY = False
if MYPY:   # pragma: no cover
    from mpfmc.core.mc import MpfMc
    from mpfmc.assets.image import ImageAsset


class ImageWidget(Widget):

    """Widget showing an image."""

    widget_type_name = 'Image'
    merge_settings = ('height', 'width')
    animation_properties = ('x', 'y', 'color', 'rotation', 'scale', 'fps', 'current_frame', 'opacity')

    def __init__(self, mc: "MpfMc", config: dict, key: Optional[str] = None, **kwargs) -> None:
        super().__init__(mc=mc, config=config, key=key)
        self.size = (0, 0)

        self._image = None  # type: ImageAsset
        self._current_loop = 0

        # Retrieve the specified image asset to display.  This widget simply
        # draws a rectangle using the texture from the loaded image asset to
        # display the image. Scaling and rotation is handled by the Scatter
        # widget.
        try:
            self._image = self.mc.images[self.config['image']]
        except KeyError:

            try:
                self._image = self.mc.images[kwargs['play_kwargs']['image']]
            except KeyError:
                pass

        if not self._image:
            if not self.mc.asset_manager.initial_assets_loaded:
                raise ValueError("Tried to use an image '{}' when the initial asset loading run has not yet been "
                                 "completed. Try to use 'init_done' as event to show your slides if you want to "
                                 "use images.".format(self.config['image']))

            raise ValueError("Cannot add Image widget. Image '{}' is not a "
                             "valid image name.".format(self.config['image']))

        # Updates the config for this widget to pull in any defaults that were
        # in the asset config
        self.merge_asset_config(self._image)

        # If the associated image asset exists, that means it's loaded already.
        if self._image.image:
            self._image_loaded()
        else:
            # if the image asset isn't loaded, we set the size to 0,0 so it
            # doesn't show up on the display yet.
            # TODO Add log about loading on demand
            self.size = (0, 0)
            self._image.load(callback=self._image_loaded)

        # Bind to all properties that when changed need to force
        # the widget to be redrawn
        self.bind(pos=self._draw_widget,
                  color=self._draw_widget,
                  rotation=self._draw_widget,
                  scale=self._draw_widget)

    def __repr__(self) -> str:  # pragma: no cover
        try:
            return '<Image name={}, size={}, pos={}>'.format(self._image.name,
                                                             self.size,
                                                             self.pos)
        except AttributeError:
            return '<Image (loading...), size={}, pos={}>'.format(self.size,
                                                                  self.pos)

    def _image_loaded(self, *args) -> None:
        """Callback when image asset has been loaded and is ready to display."""
        del args

        # Setup callback on image 'on_texture' event (called whenever the image
        # texture changes; used mainly for animated images)
        self._image.image.bind(on_texture=self._on_texture_change)
        self._on_texture_change()

        self._draw_widget()

        # Setup animation properties (if applicable)
        if self._image.image.anim_available:
            self.fps = self.config['fps']
            self.loops = self.config['loops']
            if self.config['auto_play']:
                self.play()
            else:
                self.stop()

    def _on_texture_change(self, *args) -> None:
        """Update texture from image asset (callback when image texture changes)."""
        del args

        self.texture = self._image.image.texture
        self.size = self.texture.size
        self._draw_widget()

        # Handle animation looping (when applicable)
        ci = self._image.image
        if ci.anim_available and self.loops > -1 and ci.anim_index == len(ci.image.textures) - 1:
            self._current_loop += 1
            if self._current_loop > self.loops:
                ci.anim_reset(False)
                self._current_loop = 0

    def prepare_for_removal(self) -> None:
        """Prepare the widget to be removed."""
        super().prepare_for_removal()
        # stop any animations
        try:
            self._image.image.anim_reset(False)
        # If the image was already unloaded from memory
        except AttributeError:
            pass

    def _draw_widget(self, *args):
        """Draws the image (draws a rectangle using the image texture)"""
        del args

        anchor = (self.x - self.anchor_offset_pos[0], self.y - self.anchor_offset_pos[1])
        self.canvas.clear()

        with self.canvas:
            Color(*self.color)
            Rotate(angle=self.rotation, origin=anchor)
            Scale(self.scale).origin = anchor
            Rectangle(pos=self.pos, size=self.size, texture=self.texture)

    def play(self, start_frame: Optional[int] = 0):
        """Play the image animation (if images supports it)."""
        if start_frame:
            self.current_frame = start_frame

        # pylint: disable-msg=protected-access
        self._image.image._anim_index = start_frame
        self._image.image.anim_reset(True)

    def stop(self) -> None:
        """Stop the image animation."""
        self._image.image.anim_reset(False)

    #
    # Properties
    #

    def _get_image(self) -> Optional["ImageAsset"]:
        return self._image

    image = AliasProperty(_get_image)

    texture = ObjectProperty(None, allownone=True)
    '''Texture object of the image. The texture represents the original, loaded
    image texture.

    Depending of the texture creation, the value will be a
    :class:`~kivy.graphics.texture.Texture` or a
    :class:`~kivy.graphics.texture.TextureRegion` object.

    :attr:`texture` is an :class:`~kivy.properties.ObjectProperty` and defaults
    to None.
    '''

    loops = NumericProperty(-1)
    '''Number of loops to play then stop animating. -1 means keep animating.
    '''

    def _get_fps(self) -> Optional[float]:
        if self._image.image.anim_available:
            return int(1 / self._image.image.anim_delay)
        else:
            return None

    def _set_fps(self, value: float):
        if value > 0:
            self._image.image.anim_delay = 1 / float(value)
        else:
            self._image.image.anim_delay = -1

    fps = AliasProperty(_get_fps, _set_fps)
    '''The frames per second rate for the animation if the image is sequenced
    (like an animated gif). If fps is set to 0, the animation will be stopped.
    '''

    def _get_current_frame(self) -> int:
        return self._image.image.anim_index + 1

    def _set_current_frame(self, value: Union[int, float]):
        if not self._image.image.anim_available or not hasattr(self._image.image.image, 'textures'):
            return

        frame = (int(value) - 1) % len(self._image.image.image.textures)
        if frame == self._image.image.anim_index:
            return
        else:
            self._image.image._anim_index = frame   # pylint: disable-msg=protected-access
            self._image.image.anim_reset(True)

    current_frame = AliasProperty(_get_current_frame, _set_current_frame)
    '''The current frame of the animation.
    '''

    rotation = NumericProperty(0)
    '''Rotation angle value of the widget.

    :attr:`rotation` is an :class:`~kivy.properties.NumericProperty` and defaults to
    0.
    '''

    scale = NumericProperty(1.0)
    '''Scale value of the widget.

    :attr:`scale` is an :class:`~kivy.properties.NumericProperty` and defaults to
    1.0.
    '''


widget_classes = [ImageWidget]
