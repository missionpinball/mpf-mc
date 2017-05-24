from typing import Dict
from os import path

from kivy.core.image import Image
from mpf.core.assets import Asset


class BitmapFontInfo:
    def __init__(self):
        self.face = None
        self.size = (0, 0)
        self.bold = False
        self.italic = False
        self.padding = 0
        self.spacing = 0
        self.outline = 0


class BitmapFontCommon:
    def __init__(self):
        self.line_height = 0
        self.base = 0
        self.scale_w = 0
        self.scale_h = 0


class BitmapFontCharacter:
    def __init__(self, char_id: int):
        self.char_id = char_id
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        self.xoffset = 0
        self.yoffset = 0
        self.xadvance = 0
        self.chnl = 15


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

        self._image = None  # holds the actual image in memory

        self._descriptor_file = None
        self._descriptor_list = None

        self._info = BitmapFontInfo()
        self._common = BitmapFontCommon()
        self._characters = dict()     # type: Dict[str, BitmapFontCharacter]

        # Validate the descriptor setting (it can contain either a list or None).
        # None indicates that a descriptor file will be used with the same name
        # as the font image asset file, but with a .fnt extension.
        if self.config['descriptor']:
            if isinstance(self.config['descriptor'], list):
                self._descriptor_list = self.config['descriptor']
            else:
                raise ValueError('')
        else:
            # Check if descriptor file exists
            self._descriptor_file = path.splitext(self.config['file'])[0] + '.fnt'
            if path.isfile(self._descriptor_file):
                self._load_descriptor_file()
            else:
                raise FileNotFoundError('')

    def _load_descriptor_file(self):
        pass

    def do_load(self):
        # Load the bitmap font image atlas
        self._image = Image(self.config['file'],
                            keep_data=False,
                            scale=1.0,
                            mipmap=False,
                            nocache=True)

        self._common.scale_w = self._image.width
        self._common.scale_h = self._image.height

        if self._descriptor_list:
            self._generate_character_data_from_descriptor_list()

    def _generate_character_data_from_descriptor_list(self):
        """Generates font character data from the supplied descriptor list."""

        y = 0
        row_height = int(self._common.scale_h / len(self._descriptor_list))
        self._common.line_height = row_height
        self._common.base = row_height

        for row in self._descriptor_list:
            char_width = int(self._common.scale_w / len(row))
            x = 0
            for char in row:
                character = BitmapFontCharacter(ord(char))
                character.x = x
                character.y = y
                character.height = row_height
                character.width = char_width
                character.xadvance = char_width

                self._characters[char] = character
                x += char_width

            y += row_height

    def _do_unload(self):
        self._image = None
        self._characters.clear()

