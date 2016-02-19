"""Mission Pinball Framework Media Controller (mpf-mc) setup.py"""
import os
import re

import platform
import shutil
from setuptools import setup, Extension
from Cython.Build import cythonize
from Cython.Distutils import build_ext
from os import environ
from os.path import join, dirname, sep, exists, basename, isdir, abspath
import sys


# Detect 32/64bit for OSX (http://stackoverflow.com/a/1405971/798575)
if sys.platform == 'darwin':
    if sys.maxsize > 2 ** 32:
        osx_arch = 'x86_64'
    else:
        osx_arch = 'i386'


def determine_sdl2():
    flags = {}
    sdl2_path = environ.get('KIVY_SDL2_PATH', None)

    if not sdl2_path and sys.platform == 'darwin':
        return flags

    # no pkgconfig info, or we want to use a specific sdl2 path, so perform
    # manual configuration
    flags['libraries'] = ['SDL2', 'SDL2_mixer']
    split_chr = ';' if sys.platform == 'win32' else ':'
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





# configure the env
sdl2_flags = determine_sdl2()
print(sdl2_flags)

libraries = ['SDL2', 'SDL2_mixer']

library_dirs = [join(dirname(sys.executable), 'libs')]
include_dirs = sdl2_flags['include_dirs']
extra_objects = []
extra_compile_args =['-ggdb', '-O2']
extra_link_args = []
extensions = [
    Extension(name='audio_interface',
              sources=['mpf/mc/core/audio/audio_interface.pyx'],
              include_dirs=include_dirs,
              library_dirs=library_dirs,
              libraries=libraries,
              extra_objects=extra_objects,
              extra_compile_args=extra_compile_args,
              extra_link_args=extra_link_args),
]





















# Get the version number of mpf-mc and the required version of MPF by reading
# the file directly. We can't import it because that would import mpf and
# break the setup. Details here:
# http://stackoverflow.com/questions/458550/standard-way-to-embed-version-into-python-package
version_file = "mpf/mc/_version.py"
version_file_content = open(version_file, "rt").read()
version_re = r"^__version__ = ['\"]([^'\"]*)['\"]"
mo = re.search(version_re, version_file_content, re.M)
if mo:
    mc_version = mo.group(1)
else:
    raise RuntimeError("Unable to find version string in %s." % (version_file,))

# This section pulls the MPF required version from the mpf-mc version file so
# we can write that as a requirement below
mpf_version_re = r"^__mpf_version_required__ = ['\"]([^'\"]*)['\"]"
mo = re.search(mpf_version_re, version_file_content, re.M)
if mo:
    mpf_version = mo.group(1)
else:
    raise RuntimeError("Unable to find MPF version string in %s." % (
                       version_file,))

install_requires = ['ruamel.yaml>=0.10,<0.11',
                    'mpf>={}'.format(mpf_version),
                    ]

# setup_requires = ['cython',
#                   'pygments',
#                   ]

if sys.platform == 'win32':  # win32 is x86 or x64
    install_requires += ['pypiwin32',
                         'kivy.deps.sdl2',
                         'kivy.deps.glew',
                         'kivy.deps.gstreamer_dev',
                         'kivy',
                         ]

    # setup_requires += ['kivy.deps.glew_dev',
    #                    'kivy.deps.sdl2_dev',]



# shutil.copyfile('build_scripts/distutils.cfg',
#                 os.path.join(sys.executable, 'Lib/distutils/distutils.cfg'))
#
# os.environ['USE_SDL2'] = '1'
# os.environ['USE_GSTREAMER'] = '1'

setup(

    name='mpf-mc',
    version=mc_version,
    description='Mission Pinball Framework Media Controller',
    long_description='''Graphics, video, and audio engine for the
        Mission Pinball Framework.

The Mission Pinball Framework Media Controller (MPF-MC) is a component of the
Mission Pinball Framework (MPF) that controls graphics and sound, including dot
matrix displays (DMDs), LCD displays, and color RGB LED displays.

(The MPF media controller architecture is modular, so you can use this MPF-MC
package or another one.)

The MPF-MC is built on Kivy and leverages SDL2, OpenGL, and GPU-accelerated
hardware.

MPF is a work-in-progress that is not yet complete, though we're actively
developing it and checking in several commits a week. It's MIT licensed,
actively developed by fun people, and supported by a vibrant pinball-loving
community.''',

    url='https://missionpinball.com/mpf',
    author='The Mission Pinball Framework Team',
    author_email='brian@missionpinball.com',
    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Topic :: Artistic Software',
        'Topic :: Games/Entertainment :: Arcade'

    ],

    keywords='pinball',

    include_package_data=True,

    package_data={'': ['*.yaml',
                       '*.png',
                       '*.gif',
                       '*.jpg',
                       '*.zip'
                       ]},

    packages=['mpf'],

    zip_safe=False,

    install_requires=install_requires,

    tests_require=['mock'],

    setup_requires=['cython'],

    ext_modules=cythonize(extensions),

    cmdclass= {'build_ext': build_ext}
)
