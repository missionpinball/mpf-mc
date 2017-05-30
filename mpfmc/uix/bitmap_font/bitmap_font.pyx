#!python
#cython: embedsignature=True, language_level=3

__all__ = ('BitmapFont',
           'BitmapFontException',
           '_SurfaceContainer',
           )

include 'bitmap_font.pxi'

cimport cpython.pycapsule as pycapsule

from libc.string cimport memset
from kivy.core.image import ImageData


class BitmapFontException(Exception):
    """Exception returned by the bitmap font module"""
    pass


cdef class BitmapFontCharacter:
    cdef public int id
    cdef public SDL_Rect rect
    cdef public int xoffset
    cdef public int yoffset
    cdef public int xadvance

    def __cinit__(self, *args, **kw):
        self.id = 0
        self.rect.x = 0
        self.rect.y = 0
        self.rect.w = 0
        self.rect.h = 0
        self.xoffset = 0
        self.yoffset = 0
        self.xadvance = 0


cdef class BitmapFont:
    cdef public str face
    cdef public bint bold
    cdef public bint italic
    cdef public int padding
    cdef public int spacing
    cdef public int outline

    cdef public int line_height
    cdef public int base
    cdef public int scale_w
    cdef public int scale_h

    cdef dict characters
    cdef dict kerning

    cdef SDL_Surface *image

    def __cinit__(self, *args, **kw):
        self.face = ""
        self.bold = False
        self.italic = False
        self.padding = 0
        self.spacing = 0
        self.outline = 0

        self.line_height = 0
        self.base = 0
        self.scale_w = 0
        self.scale_h = 0

        self.characters = dict()
        self.kerning = dict()

        self.image = NULL

    def __init__(self, str image_file, object descriptor):

        # Load the image file
        cdef bytes c_filename = image_file.encode('utf-8')
        cdef SDL_Surface *image = IMG_Load(c_filename)

        if image == NULL:
            raise BitmapFontException("Could not load bitmap font image file")

        self.image = image
        self.scale_w = self.image.w
        self.scale_h = self.image.h

        if isinstance(descriptor, list):
            self._load_descriptor_list(<list>descriptor)
        elif isinstance(descriptor, str):
            self._load_descriptor_file(<str>descriptor)
        else:
            raise BitmapFontException("Illegal value in bitmap font descriptor")

    def __dealloc__(self):
        if self.image != NULL:
            SDL_FreeSurface(self.image)
            self.image = NULL

    def get_image(self):
        image_capsule = pycapsule.PyCapsule_New(self.image, NULL, NULL)
        return image_capsule

    def get_characters(self):
        return self.characters

    def get_kerning(self):
        return self.kerning

    def _load_descriptor_list(self, list descriptor_list):
        cdef int x = 0
        cdef int y = 0
        cdef int row_height = int(self.scale_h / len(descriptor_list))
        cdef int char_width
        self.line_height = row_height
        self.base = row_height

        for row in descriptor_list:
            char_width = int(self.scale_w / len(row))
            x = 0
            for text_char in row:
                character = BitmapFontCharacter()
                character.id = ord(text_char)
                character.rect.x = x
                character.rect.y = y
                character.rect.w = char_width
                character.rect.h = row_height
                character.xadvance = char_width

                self.characters[text_char] = character
                x += char_width

            y += row_height

    def _load_descriptor_file(self, str descriptor_file):
        pass

    def get_descent(self):
        return self.base - self.line_height

    def get_ascent(self):
        return self.base

    def get_extents(self, str text):
        cdef int width = 0

        for text_char in text:
            char_info = self.characters[text_char]
            if char_info:
                width += char_info.xadvance

        return width, self.line_height


cdef class _SurfaceContainer:
    cdef SDL_Surface* surface
    cdef int w, h

    def __cinit__(self, w, h):
        self.surface = NULL
        self.w = w
        self.h = h

    def __init__(self, w, h):
        # XXX check on OSX to see if little endian/big endian make a difference
        # here.
        self.surface = SDL_CreateRGBSurface(0,
            w, h, 32,
            0x000000ff, 0x0000ff00, 0x00ff0000, 0xff000000)
        memset(self.surface.pixels, 0, w * h * 4)

    def __dealloc__(self):
        if self.surface != NULL:
            SDL_FreeSurface(self.surface)
            self.surface = NULL

    def render(self, container, text, x, y):
        """Render the text at the specified location."""
        cdef SDL_Rect cursor_rect
        cdef SDL_Rect source_rect
        cdef SDL_Surface *source_image

        asset = container.get_font_asset()
        if asset is None:
            return

        font = asset.bitmap_font
        if font is None:
            return

        source_image = <SDL_Surface*>pycapsule.PyCapsule_GetPointer(font.get_image(), NULL)
        if source_image == NULL:
            return

        if container.options['font_kerning']:
            # TODO: Enable kerning
            pass

        cursor_rect.x = x
        cursor_rect.y = y

        for text_char in text:
            char_info = font.get_characters()[text_char]
            if char_info:
                source_rect = char_info.rect
                SDL_BlitSurface(source_image, &source_rect, self.surface, &cursor_rect)
                cursor_rect.x += char_info.xadvance


    def get_data(self):
        """Return the bitmap font surface as ImageData (pixels)."""
        cdef int datalen = self.surface.w * self.surface.h * 4
        cdef bytes pixels = (<char *>self.surface.pixels)[:datalen]
        data = ImageData(self.w, self.h, 'rgba', pixels)
        return data


