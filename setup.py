"""Mission Pinball Framework Media Controller (mpf-mc) setup.py"""

import platform
import re

from setuptools import setup, Extension

# Get the version number of mpf-mc and the required version of MPF by reading
# the file directly. We can't import it because that would import mpf and
# break the setup. Details here:
# http://stackoverflow.com/questions/458550/standard-way-to-embed-version
# -into-python-package
version_file = "mpfmc/_version.py"
version_file_content = open(version_file, "rt").read()
version_re = r"^__version__ = ['\"]([^'\"]*)['\"]"
mo = re.search(version_re, version_file_content, re.M)
if mo:
    mc_version = mo.group(1)
else:
    raise RuntimeError(
        "Unable to find version string in %s." % (version_file,))

# This section pulls the MPF required version from the mpf-mc version file so
# we can write that as a requirement below
mpf_version_re = r"^__mpf_version_required__ = ['\"]([^'\"]*)['\"]"
mo = re.search(mpf_version_re, version_file_content, re.M)
if mo:
    mpf_version = mo.group(1)
else:
    raise RuntimeError("Unable to find MPF version string in %s." % (
        version_file,))

# figure out the system we're on so we can include the proper binaries
if platform.system() == 'Darwin':
    binary_extension = 'so'
elif platform.system() == 'Windows':
    binary_extension = 'pyd'
else:
    binary_extension = None

if binary_extension:
    package_data = {'audio_interface':
        'mpfmc/core/audio/audio_interface.{}'.format(binary_extension)}
else:
    package_data = dict()

install_requires = ['ruamel.yaml>=0.10,<0.11',
                    'mpf>={}'.format(mpf_version),
                    ]

if platform.system() == 'Windows':
    install_requires += ['pypiwin32',
                         'kivy.deps.sdl2',
                         'kivy.deps.glew',
                         'kivy.deps.gstreamer_dev',
                         'kivy',
                         ]

setup(

    name='mpf-mc',
    version=mc_version,
    description='Mission Pinball Framework Media Controller',
    long_description='''Graphics, video, and audio engine for the
        Mission Pinball Framework.

        The Mission Pinball Framework Media Controller (MPF-MC) is a component
        of the Mission Pinball Framework (MPF) that controls graphics and
        sound, including dot matrix displays (DMDs), LCD displays, and color
        RGB LED displays.

        (The MPF media controller architecture is modular, so you can use this
        MPF-MC package or another one.)

        The MPF-MC is built on Kivy and leverages SDL2, OpenGL, and
        GPU-accelerated hardware.

        MPF is a work-in-progress that is not yet complete, though we're
        actively developing it and checking in several commits a week. It's
        MIT licensed, actively developed by fun people, and supported by a
        vibrant pinball-loving community.''',

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

    package_data=package_data,

    packages=['mpfmc'],

    zip_safe=False,

    install_requires=install_requires,

    tests_require=['mock'],

    entry_points="""
    [mpf.config_player]
    sound_player=mpfmc.config_players.sound_player:register_with_mpf
    widget_player=mpfmc.config_players.widget_player:register_with_mpf
    slide_player=mpfmc.config_players.slide_player:register_with_mpf

    [mpf.command]
    mc=mpfmc.commands.mc:get_command
    """,
)
