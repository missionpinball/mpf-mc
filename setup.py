"""Mission Pinball Framework Media Controller (mpf-mc) setup.py.

Notes:
    See pyproject.toml for the rest of the setup config.
"""

import os
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
    
    # Since Windows doesn't have pkgconfig, we have to manually find the SDL2 include location. :(
    # There are so many different places where SDL2 can be installed, and options for its include folder.
    # This seems so lame, but it works.  
    
    import subprocess
    
    try:
        import kivy_deps.sdl2_dev
    except ImportError:
        raise Exception("Missing kivy_deps.sdl2_dev")
    
    sdl2_pip_data = subprocess.check_output([sys.executable, '-m', 'pip', 'show', '-f', 'kivy-deps.sdl2-dev']).decode()
    
    for line in sdl2_pip_data.splitlines():

        if line.startswith("Location:"):
            site_packages = line[10:] # strip "Location: "
            print(site_packages)
        
        elif line.endswith("SDL.h"):
            sdl2_include_path = line.strip('\SDL.h').strip()  # strip the file and the padding
            print(sdl2_include_path)
            break

    sdl2_include_path = os.path.join(site_packages, sdl2_include_path)
    print("Setting SDL2 include path:", sdl2_include_path)
    
    general_include_path = sdl2_include_path.strip('\SDL2') # strip the SDL2 folder
    print("Setting general include path:", general_include_path)

    libs_include_path = general_include_path[:-8] # strip the \include
    libs_include_path = os.path.join(libs_include_path, 'libs')
    print("Setting libs include path:", libs_include_path)
    
    audio_kws = {'define_macros': [('_THREAD_SAFE', None)],
                 'include_dirs': [sdl2_include_path, general_include_path],
                'libraries': ['SDL2_mixer', 'SDL2', 'gstreamer-1.0', 'glib-2.0', 'gobject-2.0'],
                'library_dirs': [libs_include_path]}
    
    bitmap_font_kws = {'define_macros': [('_THREAD_SAFE', None)],
                 'include_dirs': [sdl2_include_path, general_include_path],
                 'libraries': ['SDL2', 'SDL2_image'],
                'library_dirs': [libs_include_path]}
    
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