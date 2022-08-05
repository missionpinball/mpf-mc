"""Mission Pinball Framework Media Controller (mpf-mc) setup.py.

Notes:
    See pyproject.toml for the rest of the setup config.
"""

import sys

if sys.platform != 'win32':
    import pkgconfig as pc

from collections import defaultdict
from setuptools import Extension, setup

sound_file_source = 'mpfmc/core/audio/sound_file.pyx',
track_source = 'mpfmc/core/audio/track.pyx',
track_standard_source = 'mpfmc/core/audio/track_standard.pyx',
track_sound_loop_source = 'mpfmc/core/audio/track_sound_loop.pyx',
audio_interface_source = 'mpfmc/core/audio/audio_interface.pyx',
playlist_controller_source = 'mpfmc/core/audio/playlist_controller.pyx',
bitmap_font_source = 'mpfmc/uix/bitmap_font/bitmap_font.pyx',

cython_sources = [
    sound_file_source,
    track_source,
    track_standard_source,
    track_sound_loop_source,
    audio_interface_source,
    playlist_controller_source,
    bitmap_font_source,
]

ext_libs = ['sdl2', 'SDL2_image', 'SDL2_mixer', 'SDL2_ttf', 'gstreamer-1.0']

if sys.platform != 'win32':
    for lib in ext_libs:
        if not pc.exists(lib):
            raise Exception(f"Missing {lib}")

def members_appended(*ds):
        result = defaultdict(list)
        for d in ds:
            for k, v in d.items():
                assert isinstance(v, list)
                result[k].extend(v)
        return result

if sys.platform == 'win32':
    
    import pathlib
    
    posix_prefix = pathlib.PureWindowsPath(repr(sys.prefix)).as_posix()
    
    audio_kws = {'define_macros': [('_THREAD_SAFE', None)],
                 'include_dirs': [f'{posix_prefix}/include/SDL2'],
                 'libraries': ['SDL2_mixer', 'SDL2', 'gstreamer-1.0', 'glib-2.0', 'gobject-2.0']}
    
    bitmap_font_kws = {'define_macros': [('_THREAD_SAFE', None)],
                 'include_dirs': [f'{posix_prefix}/include/SDL2'],
                 'libraries': ['SDL2', 'SDL2_image']}
    
else:
    audio_kws = members_appended(pc.parse('SDL2_mixer'), pc.parse('gstreamer-1.0'))
    bitmap_font_kws = members_appended(pc.parse('SDL2'), pc.parse('SDL2_image'))

ext_modules = [
    Extension('mpfmc.core.audio.sound_file', [*sound_file_source], **audio_kws ,),
    Extension('mpfmc.core.audio.track', [*track_source], **audio_kws),
    Extension('mpfmc.core.audio.track_standard', [*track_standard_source], **audio_kws),
    Extension('mpfmc.core.audio.track_sound_loop', [*track_sound_loop_source], **audio_kws),
    Extension('mpfmc.core.audio.audio_interface', [*audio_interface_source], **audio_kws),
    Extension('mpfmc.core.audio.playlist_controller', [*playlist_controller_source], **audio_kws),
    Extension('mpfmc.uix.bitmap_font.bitmap_font', [*bitmap_font_source], **bitmap_font_kws,)
]

setup(
    ext_modules=ext_modules,
)