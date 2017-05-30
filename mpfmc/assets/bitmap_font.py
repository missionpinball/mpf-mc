from typing import TYPE_CHECKING, Dict, Optional
from os import path

from kivy.core.image import Image
from kivy.core.image import ImageData

from mpf.core.assets import Asset
from mpfmc.uix.bitmap_font.bitmap_font import BitmapFont


class BitmapFontAsset(Asset):

    attribute = 'bitmap_fonts'
    path_string = 'bitmap_fonts'
    config_section = 'bitmap_fonts'
    extensions = ('png', 'gif', 'bmp')
    class_priority = 100
    pool_config_section = None
    asset_group_class = None

    def __init__(self, mc, name, file, config):
        super().__init__(mc, name, file, config)

        self._bitmap_font = None  # holds the actual image and font info in memory
        self._descriptor_file = None

        # Validate the descriptor setting (it can contain either a list, or a
        # descriptor file name).  If the descriptor setting is omitted, a file
        # will be used with the same name as the font image asset file, but with a
        # .fnt extension.
        if 'descriptor' not in self.config:
            self.config['descriptor'] = path.splitext(self.config['file'])[0] + '.fnt'

        if isinstance(self.config['descriptor'], str):
            if not path.isfile(self.config['descriptor']):
                raise FileNotFoundError('Could not locate the bitmap font descriptor file ' +
                                        self._descriptor_file)

        elif not isinstance(self.config['descriptor'], list):
            raise ValueError('Bitmap font descriptor must contain either a list or file name.')

    @property
    def bitmap_font(self):
        return self._bitmap_font

    def get_extents(self, text):
        if self._bitmap_font:
            return self.bitmap_font.get_extents(text)
        else:
            return 0, 0

    def get_descent(self):
        if self._bitmap_font:
            return self.bitmap_font.get_descent()
        else:
            return 0

    def get_ascent(self):
        if self._bitmap_font:
            return self.bitmap_font.get_ascent()
        else:
            return 0

    def do_load(self):
        # Load the bitmap font image atlas
        self._bitmap_font = BitmapFont(self.config['file'], self.config['descriptor'])

    def _do_unload(self):
        self._bitmap_font = None

    def render_text(self, text, texture, x, y, color):
        cursor_x = x
        cursor_y = y
        previous_char = None

        for char in text:
            cursor_x += self.get_kerning(previous_char, char)
            char_info = self._characters[char]
            texture.blit_buffer(size=char_info.texture_region.size,
                                colorfmt=self.colorfmt,
                                pos=(cursor_x, cursor_y),
                                pbuffer=char_info.texture_region.pixels)

            # TODO: Add offsets
            cursor_x += char_info.xadvance
            previous_char = char
