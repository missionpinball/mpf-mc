"""Mission Pinball Framework Media Controller (mpf-mc) setup.py.

Notes:
    See pyproject.toml for the rest of the setup config.
"""

import sys

if sys.platform != 'win32':
    import pkgconfig as pc

from collections import defaultdict
from os.path import abspath, exists, join, isdir
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

def get_isolated_env_paths():
    try:
        # sdl2_dev is installed before setup.py is run, when installing from
        # source due to pyproject.toml. However, it is installed to a
        # pip isolated env, which we need to add to compiler
        import kivy_deps.sdl2_dev as sdl2_dev
    except ImportError:
        return [], []

    root = abspath(join(sdl2_dev.__path__[0], '../../../..'))
    includes = [join(root, 'Include')] if isdir(join(root, 'Include')) else []
    libs = [join(root, 'libs')] if isdir(join(root, 'libs')) else []
    return includes, libs

def determine_sdl2():
    flags = {}

    includes, _ = get_isolated_env_paths()

    # no pkgconfig info, or we want to use a specific sdl2 path, so perform
    # manual configuration
    flags['libraries'] = ['SDL2', 'SDL2_ttf', 'SDL2_image', 'SDL2_mixer']
    split_chr = ';' if sys.platform == 'win32' else ':'


    sdl2_paths = []
    for include in includes + [join(sys.prefix, 'include')]:
        sdl_inc = join(include, 'SDL2')
        if isdir(sdl_inc):
            sdl2_paths.append(sdl_inc)
    
    flags['include_dirs'] = sdl2_paths
    flags['extra_link_args'] = []
    flags['extra_compile_args'] = []
    flags['library_dirs'] = sdl2_paths

    # ensure headers for all the SDL2 and sub libraries are available
    libs_to_check = ['SDL', 'SDL_mixer', 'SDL_ttf', 'SDL_image']
    can_compile = True
    for lib in libs_to_check:
        found = False
        for d in flags['include_dirs']:
            fn = join(d, '{}.h'.format(lib))
            if exists(fn):
                found = True
                print('SDL2: found {} header at {}'.format(lib, fn))
                break

        if not found:
            print('SDL2: missing sub library {}'.format(lib))
            can_compile = False

    return flags

if sys.platform == 'win32':
    
    # Since Windows doesn't have pkgconfig, we have to manually find the SDL2 include location. :(
    # There are so many different places where SDL2 can be installed, and options for its include folder.
    # This seems so lame, but it works.  
    
    # import subprocess
    
    # try:
    #     import kivy_deps.sdl2_dev
    #     print("Found kivy_deps.sdl2_dev")
    #     print(kivy_deps.sdl2_dev.__path__)
    # except ImportError:
    #     raise Exception("Missing kivy_deps.sdl2_dev")
    
    # print("installed packages")
    # import pkgutil
    # for i in pkgutil.iter_modules(None):
    #     print(i)
    
    # sdl2_pip_data = subprocess.check_output([sys.executable, '-m', 'pip', 'show', '-f', 'kivy-deps.sdl2-dev']).decode()
    
    # for line in sdl2_pip_data.splitlines():

    #     if line.startswith("Location:"):
    #         site_packages = line[10:] # strip "Location: "
    #         print(site_packages)
        
    #     elif line.endswith("SDL.h"):
    #         sdl2_include_path = line.strip('\SDL.h').strip()  # strip the file and the padding
    #         print(sdl2_include_path)
    #         break

    sdl2_include_path = determine_sdl2()['include_dirs'][0]
    print("Setting SDL2 include path:", sdl2_include_path)
    
    general_include_path = sdl2_include_path.strip('\SDL2') # strip the SDL2 folder
    print("Setting general include path:", general_include_path)

    libs_include_path = general_include_path[:-8] # strip the \include
    libs_include_path = join(libs_include_path, 'libs')
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
    Extension('mpfmc.core.audio.sound_file', [*sound_file_source], **audio_kws),
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