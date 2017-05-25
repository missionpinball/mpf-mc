from typing import TYPE_CHECKING

from kivy.core.text import LabelBase
from kivy.graphics.fbo import Fbo
from kivy.core.image import ImageData

from mpfmc.assets.bitmap_font import BitmapFontAsset
from mpfmc.core.mc import MpfMc


class LabelBitmapFont(LabelBase):

    def __init__(self, mc: MpfMc, font_name, text='', color=None, **kwargs):
        del kwargs
        self.mc = mc
        super().__init__(text=text, font_name=font_name, color=color)

    def _get_font(self) -> BitmapFontAsset:
        return self.mc.bitmap_fonts[self.options['font_name_r']]

    def resolve_font_name(self):
        """Resolves the supplied bitmap font name."""
        options = self.options
        fontname = options['font_name']

        if fontname in self.mc.bitmap_fonts:
            options['font_name_r'] = fontname
        else:
            raise ValueError('LabelBitmapFont: font_name %s not found in bitmap_fonts.' % fontname)

    def get_extents(self, text):
        bitmap_font = self._get_font()
        return bitmap_font.get_extents(text)

    def get_descent(self):
        bitmap_font = self._get_font()
        return bitmap_font.get_descent()

    def get_ascent(self):
        bitmap_font = self._get_font()
        return bitmap_font.get_ascent()

    def _render_begin(self):
        self._fbo = Fbo(size=self.size)
        self._fbo.clear()

    def _render_text(self, text, x, y):
        bitmap_font = self._get_font()
        color = self.options['color']
        bitmap_font.render_text(text, self._fbo, x, y, color)

    def _render_end(self):
        self._fbo.draw()
        data = ImageData(self._size[0], self._size[1], 'rgba', self._fbo.pixels)
        del self._fbo
        return data
