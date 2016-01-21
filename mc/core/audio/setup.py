# cython: language_level=3

from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize
from os import environ


# configure the env
libraries = ['libSDL2', 'libSDL2_mixer']
library_dirs = [environ.get('KIVY_PORTABLE_ROOT') + 'SDL2\lib']
include_dirs = [environ.get('KIVY_PORTABLE_ROOT') + 'SDL2\include\SDL2']
extra_objects = []
extra_compile_args =['-ggdb', '-O2']
extra_link_args = []
extensions = [
    Extension('audio_interface',
              ['audio_interface.pyx'],
              include_dirs=include_dirs,
              library_dirs=library_dirs,
              libraries=libraries,
              extra_objects=extra_objects,
              extra_compile_args=extra_compile_args,
              extra_link_args=extra_link_args),

    Extension('functions',
              ['functions.pyx'],
              include_dirs=include_dirs,
              library_dirs=library_dirs,
              libraries=libraries,
              extra_objects=extra_objects,
              extra_compile_args=extra_compile_args,
              extra_link_args=extra_link_args)
]

setup(
    name="audio",
    ext_modules=cythonize(extensions),
)
