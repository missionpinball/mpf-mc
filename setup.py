"""Mission Pinball Framework Media Controller (mpf-mc) setup.py"""

from platform import system

from setuptools import setup, find_packages

import mpf.mc

install_requires = ['ruamel.yaml',
                    'mpf',
                    ]

if system() == 'Windows':

    install_requires += ['pypiwin32',
                         'kivy.deps.sdl2',
                         'kivy.deps.glew',
                         'kivy.deps.gstreamer_dev',
                         'kivy',
                         ]

setup(

    name='mpf-mc',
    version=mpf.mc.__version__,
    description='Mission Pinball Framework Media Controller',
    long_description='''Graphics, video, and audio engine for the
        Mission Pinball Framework.

The Mission Pinball Framework (MPF) is an open source, cross-platform,
Python-based software framework for powering real pinball machines.

The Mission Pinball Framework Media Controller (MPF-MC, this package) is the
component of MPF that controls graphics and sound, including DMDs,
architecture is modular, with multiple options for driving graphics and
sound. This MPF-MC package is one option, and there's another option based
on Unity 3D.

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

    packages=find_packages(),

    # zip_safe=True,

    install_requires=install_requires,

    tests_require=['mock']
)
