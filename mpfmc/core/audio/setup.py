# cython: language_level=3

"""
The custom MPF MC audio library can be compiled and built using this script.
The environment should be setup exactly like the environment for building
Kivy.  See https://kivy.org/docs/installation/installation.html for more
information.
"""

from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize
from os import environ
from os.path import join, dirname, exists, isdir
from copy import deepcopy
import sys


def getoutput(cmd):
    import subprocess
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    p.wait()
    if p.returncode:  # if not returncode == 0
        print('WARNING: A problem occured while running {0} (code {1})\n'
              .format(cmd, p.returncode))
        stderr_content = p.stderr.read()
        if stderr_content:
            print('{0}\n'.format(stderr_content))
        return ""
    return p.stdout.read()

def pkgconfig(*packages, **kw):
    flag_map = {'-I': 'include_dirs', '-L': 'library_dirs', '-l': 'libraries'}
    cmd = 'pkg-config --libs --cflags {}'.format(' '.join(packages))
    results = getoutput(cmd).split()
    for token in results:
        ext = token[:2].decode('utf-8')
        flag = flag_map.get(ext)
        if not flag:
            continue
        kw.setdefault(flag, []).append(token[2:].decode('utf-8'))
    return kw

def merge(d1, *args):
    d1 = deepcopy(d1)
    for d2 in args:
        for key, value in d2.items():
            value = deepcopy(value)
            if key in d1:
                d1[key].extend(value)
            else:
                d1[key] = value
    return d1


platform = sys.platform

# Detect 32/64bit for OSX (http://stackoverflow.com/a/1405971/798575)
if sys.platform == 'darwin':
    if sys.maxsize > 2 ** 32:
        osx_arch = 'x86_64'
    else:
        osx_arch = 'i386'


def determine_sdl2():
    flags = {}
    sdl2_path = environ.get('KIVY_SDL2_PATH', None)

    if not sdl2_path and platform == 'darwin':
        return flags

    # no pkgconfig info, or we want to use a specific sdl2 path, so perform
    # manual configuration
    flags['libraries'] = ['SDL2', 'SDL2_mixer']
    split_chr = ';' if platform == 'win32' else ':'
    sdl2_paths = sdl2_path.split(split_chr) if sdl2_path else []

    if not sdl2_paths:
        sdl_inc = join(dirname(sys.executable), 'include', 'SDL2')
        if isdir(sdl_inc):
            sdl2_paths = [sdl_inc]
        sdl2_paths.extend(['/usr/local/include/SDL2', '/usr/include/SDL2'])

    flags['include_dirs'] = sdl2_paths

    flags['extra_link_args'] = []
    flags['extra_compile_args'] = []
    flags['extra_link_args'] += (
        ['-L' + p for p in sdl2_paths] if sdl2_paths else
        ['-L/usr/local/lib/'])

    # ensure headers for all the SDL2 and sub libraries are available
    libs_to_check = ['SDL', 'SDL_mixer']
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

    if not can_compile:
        return {}

    return flags


gst_flags = pkgconfig('gstreamer-1.0')
print("gst_flags:", gst_flags)
if 'libraries' not in gst_flags:
    print('Missing GStreamer framework')
    raise EnvironmentError('Missing GStreamer framework')

# configure the env
sdl2_flags = determine_sdl2()

if 'libraries' not in sdl2_flags:
    print('Missing SDL2 framework')
    raise EnvironmentError('Missing SDL2 framework')

flags = merge(gst_flags, sdl2_flags)
print(flags)

libraries = flags['libraries']
library_dirs = [join(dirname(sys.executable), 'libs')]
include_dirs = flags['include_dirs']
extra_objects = []
extra_compile_args = ['-ggdb', '-O2'].append(flags['extra_compile_args'])
extra_link_args = flags['extra_link_args']
extensions = [
    Extension('audio_interface',
              ['audio_interface.pyx'],
              include_dirs=include_dirs,
              library_dirs=library_dirs,
              libraries=libraries,
              extra_objects=extra_objects,
              extra_compile_args=extra_compile_args,
              extra_link_args=extra_link_args),
]

setup(
    name="audio",
    ext_modules=cythonize(extensions),
)
