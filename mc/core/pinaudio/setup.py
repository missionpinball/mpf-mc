# cython: language_level=3

import sys
import os
from os.path import join, dirname
from os import environ
from distutils.core import setup
from distutils.extension import Extension

platform = sys.platform

# ensure Cython is installed for desktop app
have_cython = False
cmdclass = {}
try:
    from Cython.Distutils import build_ext
    have_cython = True
    cmdclass['build_ext'] = build_ext
except ImportError:
    print('**** Cython is required to compile audiostream ****')
    raise

# configure the env
libraries = ['libSDL2', 'libSDL2_mixer']
library_dirs = [environ.get('KIVY_PORTABLE_ROOT') + 'SDL2\lib']
include_dirs = [environ.get('KIVY_PORTABLE_ROOT') + 'SDL2\include\SDL2']
extra_objects = []
extra_compile_args =['-ggdb', '-O2']
extra_link_args = []
extensions = []


# generate an Extension object from its dotted name
def makeExtension(extName, files=None):
    extPath = extName.replace('.', os.path.sep) + (
            '.c' if not have_cython else '.pyx')
    if files is None:
        files = []
    print("Extension: {} {} {}".format(extName, extPath, extra_objects))
    return Extension(
        extName,
        [extPath] + files,
        include_dirs=include_dirs,
        library_dirs=library_dirs,
        libraries=libraries,
        extra_objects=extra_objects,
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args
        )

config_pxi = join(dirname(__file__), 'pinaudio', 'config.pxi')
with open(config_pxi, 'w') as fd:
    fd.write('DEF PLATFORM = "{}"'.format(platform))


# indicate which extensions we want to compile
extensions += [makeExtension('pinaudio.core')]

setup(
    name='pinaudio',
    version='0.01',
    author='Quinn Capen',
    author_email='',
    packages=['pinaudio'],
    url='http://missionpinball.com/',
    license='MIT',
    description='An audio library designed to let the user stream to speakers',
    ext_modules=extensions,
    cmdclass=cmdclass,
)
