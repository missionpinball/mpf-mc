from kivy.core.text import LabelBase

from mpfmc.assets.bitmap_font import BitmapFontAsset
from mpfmc.uix.bitmap_font.bitmap_font import _SurfaceContainer
from mpfmc.core.mc import MpfMc


class LabelBitmapFont(LabelBase):

    def __init__(self, mc: MpfMc, font_name, text='', font_kerning=True, **kwargs):
        del kwargs
        self.mc = mc
        self._surface = None
        super().__init__(text=text, font_name=font_name, font_kerning=font_kerning)

    def get_font_asset(self) -> BitmapFontAsset:
        """Return the bitmap font asset used for this label."""
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
        options = self.options
        bitmap_font = self.get_font_asset()
        return bitmap_font.get_extents(text, options['font_kerning'])

    def get_descent(self):
        bitmap_font = self.get_font_asset()
        return bitmap_font.get_descent()

    def get_ascent(self):
        bitmap_font = self.get_font_asset()
        return bitmap_font.get_ascent()

    def _render_begin(self):
        self._surface = _SurfaceContainer(self.size[0], self.size[1])

    def _render_text(self, text, x, y):
        self._surface.render(self, text, x, y)

    def _render_end(self):
        return self._surface.get_data()
