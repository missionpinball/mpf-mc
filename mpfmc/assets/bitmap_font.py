from os import path

from mpfmc.uix.bitmap_font.bitmap_font import BitmapFont

from mpfmc.assets.mc_asset import McAsset


class BitmapFontAsset(McAsset):

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

        # Validate the descriptor setting (it can contain either a list, or a
        # descriptor file name).  If the descriptor setting is omitted, a file
        # will be used with the same name as the font image asset file, but with a
        # .fnt extension.
        if 'descriptor' not in self.config or not self.config['descriptor']:
            self.config['descriptor'] = path.splitext(self.config['file'])[0] + '.fnt'

        if isinstance(self.config['descriptor'], str):
            if not path.isfile(self.config['descriptor']):
                raise FileNotFoundError('Could not locate the bitmap font descriptor file {}'.format(
                                        self.config['descriptor']))

        elif not isinstance(self.config['descriptor'], list):
            raise ValueError('Bitmap font descriptor must contain either a list or file name.')

    @property
    def bitmap_font(self):
        return self._bitmap_font

    def get_extents(self, text, font_kerning=True):
        if self._bitmap_font:
            return self.bitmap_font.get_extents(text, font_kerning)

        return 0, 0

    def get_descent(self):
        if self._bitmap_font:
            return self.bitmap_font.get_descent()

        return 0

    def get_ascent(self):
        if self._bitmap_font:
            return self.bitmap_font.get_ascent()

        return 0

    def do_load(self):
        # Load the bitmap font image atlas
        self._bitmap_font = BitmapFont(self.config['file'], self.config['descriptor'])

    def _do_unload(self):
        self._bitmap_font = None
