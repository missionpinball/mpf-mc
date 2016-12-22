"""Mission Pinball Framework Media Controller (mpf-mc) setup.py"""


import sys
import re

from copy import deepcopy
import os
from os.path import join, dirname, sep, exists, basename, isdir
from os import walk, environ
from distutils.version import LooseVersion
from collections import OrderedDict
from time import sleep
from setuptools import setup, Extension


# fix error with py3's LooseVersion comparisons
def ver_equal(self, other):
    return self.version == other

LooseVersion.__eq__ = ver_equal


MIN_CYTHON_STRING = '0.23'
MIN_CYTHON_VERSION = LooseVersion(MIN_CYTHON_STRING)
MAX_CYTHON_STRING = '0.24.1'
MAX_CYTHON_VERSION = LooseVersion(MAX_CYTHON_STRING)
CYTHON_UNSUPPORTED = ()

PACKAGE_FILES_ALLOWED_EXT = ('py', 'yaml', 'png', 'md', 'zip', 'gif', 'jpg',
                             'mp4', 'm4v', 'so', 'pyd', 'dylib', 'wav', 'ogg',
                             'pxi', 'pyx', 'c', 'h', 'ttf')


def getoutput(cmd, env=None):
    import subprocess
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, env=env)
    p.wait()
    if p.returncode:  # if not returncode == 0
        print('WARNING: A problem occurred while running {0} (code {1})\n'
              .format(cmd, p.returncode))
        stderr_content = p.stderr.read()
        if stderr_content:
            print('{0}\n'.format(stderr_content))
        return ""
    return p.stdout.read()


def pkgconfig(*packages, **kw):
    flag_map = {'-I': 'include_dirs', '-L': 'library_dirs', '-l': 'libraries'}
    lenviron = None
    pconfig = join(dirname(sys.executable), 'libs', 'pkgconfig')

    if isdir(pconfig):
        lenviron = environ.copy()
        lenviron['PKG_CONFIG_PATH'] = '{};{}'.format(
            environ.get('PKG_CONFIG_PATH', ''), pconfig)
    cmd = 'pkg-config --libs --cflags {}'.format(' '.join(packages))
    results = getoutput(cmd, lenviron).split()
    for token in results:
        ext = token[:2].decode('utf-8')
        flag = flag_map.get(ext)
        if not flag:
            continue
        kw.setdefault(flag, []).append(token[2:].decode('utf-8'))
    return kw


# -----------------------------------------------------------------------------
# Determine on which platform we are

platform = sys.platform

# Detect 32/64bit for OSX (http://stackoverflow.com/a/1405971/798575)
if sys.platform == 'darwin':
    if sys.maxsize > 2 ** 32:
        osx_arch = 'x86_64'
    else:
        osx_arch = 'i386'

if exists('/opt/vc/include/bcm_host.h'):
    platform = 'rpi'
if exists('/usr/lib/arm-linux-gnueabihf/libMali.so'):
    platform = 'mali'

# -----------------------------------------------------------------------------
# Detect options
#
c_options = OrderedDict()
c_options['use_rpi'] = platform == 'rpi'
c_options['use_mali'] = platform == 'mali'
c_options['use_osx_frameworks'] = platform == 'darwin'

# SDL2 and GStreamer are required for mpfmc
c_options['use_sdl2'] = True
c_options['use_gstreamer'] = True

# now check if environ is changing the default values
for key in list(c_options.keys()):
    ukey = key.upper()
    if ukey in environ:
        value = bool(int(environ[ukey]))
        print('Environ change {0} -> {1}'.format(key, value))
        c_options[key] = value

if not c_options['use_sdl2']:
    print('SDL2 framework is required for mpfmc compilation')
    raise EnvironmentError('SDL2 framework is required for mpfmc compilation')

if not c_options['use_gstreamer']:
    print('GStreamer framework is required for mpfmc compilation')
    raise EnvironmentError('GStreamer framework is required for mpfmc compilation')


# -----------------------------------------------------------------------------
# Cython check
#
cython_unsupported_append = '''

  Please note that the following versions of Cython are not supported
  at all: {}
'''.format(', '.join(map(str, CYTHON_UNSUPPORTED)))

cython_min = '''\
  This version of Cython is not compatible with Kivy. Please upgrade to
  at least version {0}, preferably the newest supported version {1}.

  If your platform provides a Cython package, make sure you have upgraded
  to the newest version. If the newest version available is still too low,
  please remove it and install the newest supported Cython via pip:

    pip install -I Cython=={1}{2}\
'''.format(MIN_CYTHON_STRING, MAX_CYTHON_STRING,
           cython_unsupported_append if CYTHON_UNSUPPORTED else '')

cython_max = '''\
  This version of Cython is untested with Kivy. While this version may
  work perfectly fine, it is possible that you may experience issues. If
  you do have issues, please downgrade to a supported version. It is
  best to use the newest supported version, {1}, but the minimum
  supported version is {0}.

  If your platform provides a Cython package, check if you can downgrade
  to a supported version. Otherwise, uninstall the platform package and
  install Cython via pip:

    pip install -I Cython=={1}{2}\
'''.format(MIN_CYTHON_STRING, MAX_CYTHON_STRING,
           cython_unsupported_append if CYTHON_UNSUPPORTED else '')

cython_unsupported = '''\
  This version of Cython suffers from known bugs and is unsupported.
  Please install the newest supported version, {1}, if possible, but
  the minimum supported version is {0}.

  If your platform provides a Cython package, check if you can install
  a supported version. Otherwise, uninstall the platform package and
  install Cython via pip:

    pip install -I Cython=={1}{2}\
'''.format(MIN_CYTHON_STRING, MAX_CYTHON_STRING,
           cython_unsupported_append)

have_cython = False
skip_cython = False
try:
    # check for cython
    from Cython.Distutils import build_ext
    have_cython = True
    import Cython
    cy_version_str = Cython.__version__
    cy_ver = LooseVersion(cy_version_str)
    print('\nDetected Cython version {}'.format(cy_version_str))
    if cy_ver < MIN_CYTHON_VERSION:
        print(cython_min)
        raise ImportError('Incompatible Cython Version')
    if cy_ver in CYTHON_UNSUPPORTED:
        print(cython_unsupported)
        raise ImportError('Incompatible Cython Version')
    if cy_ver > MAX_CYTHON_VERSION:
        print(cython_max)
        sleep(1)
except ImportError:
    print('\nCython is missing, its required for compiling mpfmc !\n\n')
    raise

if not have_cython:
    from distutils.command.build_ext import build_ext

# -----------------------------------------------------------------------------
# Setup classes

# the build path where mpfmc is being compiled
src_path = build_path = dirname(__file__)

if platform == 'darwin':
    if c_options['use_osx_frameworks']:
        if osx_arch == "i386":
            print("Warning: building with frameworks fail on i386")
        else:
            print("OSX framework used, force to x86_64 only")
            environ["ARCHFLAGS"] = environ.get("ARCHFLAGS", "-arch x86_64")
            print("OSX ARCHFLAGS are: {}".format(environ["ARCHFLAGS"]))

gst_flags = {}

# detect gstreamer, only on desktop
# works if we forced the options or in autodetection
if platform not in ('ios', 'android') and (c_options['use_gstreamer']
                                           in (None, True)):
    if c_options['use_osx_frameworks'] and platform == 'darwin':
        # check the existence of frameworks
        f_path = '/Library/Frameworks/GStreamer.framework'
        if not exists(f_path):
            c_options['use_gstreamer'] = False
            print('Missing GStreamer framework {}'.format(f_path))
            raise EnvironmentError('Missing GStreamer framework {}'.format(f_path))

        else:
            c_options['use_gstreamer'] = True
            gst_flags = {
                'extra_link_args': [
                    '-F/Library/Frameworks',
                    '-Xlinker', '-rpath',
                    '-Xlinker', '/Library/Frameworks',
                    '-Xlinker', '-headerpad',
                    '-Xlinker', '190',
                    '-framework', 'GStreamer'],
                'include_dirs': [join(f_path, 'Headers')]}

    else:
        # use pkg-config approach instead
        gst_flags = pkgconfig('gstreamer-1.0')
        if 'libraries' in gst_flags:
            c_options['use_gstreamer'] = True


# detect SDL2, only on desktop and iOS, or android if explicitly enabled
# works if we forced the options or in autodetection
sdl2_flags = {}
if c_options['use_sdl2'] or (
        platform not in ('android',) and c_options['use_sdl2'] is None):

    if c_options['use_osx_frameworks'] and platform == 'darwin':
        # check the existence of frameworks
        sdl2_valid = True
        sdl2_flags = {
            'extra_link_args': [
                '-F/Library/Frameworks',
                '-Xlinker', '-rpath',
                '-Xlinker', '/Library/Frameworks',
                '-Xlinker', '-headerpad',
                '-Xlinker', '190'],
            'include_dirs': [],
            'extra_compile_args': ['-F/Library/Frameworks']
        }
        f_path = '/Library/Frameworks/{}.framework'.format('SDL2')
        if exists(f_path):
            sdl2_flags['extra_link_args'] += ['-framework', 'SDL2']
            sdl2_flags['include_dirs'] += [join(f_path, 'Headers')]
            print('Found sdl2 frameworks: {}'.format(f_path))
        else:
            print('Missing framework {}'.format(f_path))
            sdl2_valid = False

        if not sdl2_valid:
            c_options['use_sdl2'] = False
            print('Cannot perform mpfmc compilation due to missing SDL2 framework')
            raise EnvironmentError('Cannot perform mpfmc compilation due to missing SDL2 framework')
        else:
            c_options['use_sdl2'] = True
            print('Activate SDL2 compilation')

    elif platform != "ios":
        # use pkg-config approach instead
        sdl2_flags = pkgconfig('sdl2')
        if 'libraries' in sdl2_flags:
            c_options['use_sdl2'] = True
        else:
            print('Cannot perform mpfmc compilation due to missing SDL2 framework')
            raise EnvironmentError('Cannot perform mpfmc compilation due to missing SDL2 framework')


# -----------------------------------------------------------------------------
# declare flags


def get_modulename_from_file(filename):
    print(filename)
    filename = filename.replace(sep, '/')
    pyx = '.'.join(filename.split('.')[:-1])
    pyxl = pyx.split('/')
    while pyxl[0] != 'mpfmc':
        pyxl.pop(0)
    if pyxl[1] == 'mpfmc':
        pyxl.pop(0)
    return '.'.join(pyxl)


def expand(root, *args):
    return join(root, 'mpfmc', *args)


class CythonExtension(Extension):

    def __init__(self, *args, **kwargs):
        Extension.__init__(self, *args, **kwargs)
        self.cython_directives = {
            'c_string_encoding': 'utf-8',
            'profile': 'USE_PROFILE' in environ,
            'embedsignature': 'USE_EMBEDSIGNATURE' in environ}
        # XXX with pip, setuptools is imported before distutils, and change
        # our pyx to c, then, cythonize doesn't happen. So force again our
        # sources
        self.sources = args[1]


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


def determine_base_flags():
    flags = {
        'libraries': [],
        'include_dirs': [],
        'extra_link_args': [],
        'extra_compile_args': []}
    if platform.startswith('freebsd'):
        flags['include_dirs'] += [join(
            environ.get('LOCALBASE', '/usr/local'), 'include')]
        flags['extra_link_args'] += ['-L', join(
            environ.get('LOCALBASE', '/usr/local'), 'lib')]
    elif platform == 'darwin':
        v = os.uname()
        if v[2] >= '13.0.0':
            # use xcode-select to search on the right Xcode path
            # XXX use the best SDK available instead of a specific one
            import platform as _platform
            xcode_dev = getoutput('xcode-select -p').splitlines()[0]
            sdk_mac_ver = '.'.join(_platform.mac_ver()[0].split('.')[:2])
            print('Xcode detected at {}, and using OS X{} sdk'.format(
                    xcode_dev, sdk_mac_ver))
            sysroot = join(
                    xcode_dev.decode('utf-8'),
                    'Platforms/MacOSX.platform/Developer/SDKs',
                    'MacOSX{}.sdk'.format(sdk_mac_ver),
                    'System/Library/Frameworks')
        else:
            sysroot = ('/System/Library/Frameworks/'
                       'ApplicationServices.framework/Frameworks')
        flags['extra_compile_args'] += ['-F%s' % sysroot]
        flags['extra_link_args'] += ['-F%s' % sysroot]
    return flags


def determine_sdl2():
    flags = {}
    if not c_options['use_sdl2']:
        return flags

    sdl2_path = environ.get('KIVY_SDL2_PATH', None)

    if sdl2_flags and not sdl2_path and platform == 'darwin':
        return sdl2_flags

    # no pkgconfig info, or we want to use a specific sdl2 path, so perform
    # manual configuration
    flags['libraries'] = ['SDL2',]
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

    # ensure headers for all the SDL2 library is available
    libs_to_check = ['SDL',]
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
            print('SDL2: missing library {}'.format(lib))
            can_compile = False

    if not can_compile:
        c_options['use_sdl2'] = False
        print('Cannot perform mpfmc compilation due to missing SDL2 framework')
        raise EnvironmentError('Cannot perform mpfmc compilation due to missing SDL2 framework')

    return flags


base_flags = determine_base_flags()
gl_flags = {}

# -----------------------------------------------------------------------------
# sources to compile
sources = {}

if c_options['use_sdl2'] and c_options['use_gstreamer']:
    sdl2_flags = determine_sdl2()
    if sdl2_flags:
        sdl2_depends = {'depends': ['core/audio/sdl2_helper.h', 'core/audio/sdl2.pxi',]}
        gst_depends = {'depends': ['core/audio/gstreamer_helper.h', 'core/audio/gstreamer.pxi',]}
        for source_file in ('core/audio/audio_interface.pyx',):
            sources[source_file] = merge(
                base_flags, gst_flags, gst_depends, sdl2_flags, sdl2_depends)

# -----------------------------------------------------------------------------
# extension modules

def get_extensions_from_sources(sources):
    ext_modules = []
    if environ.get('KIVY_FAKE_BUILDEXT'):
        print('Fake build_ext asked, will generate only .h/.c')
        return ext_modules
    for pyx, flags in sources.items():
        pyx = expand(src_path, pyx)
        depends = [expand(src_path, x) for x in flags.pop('depends', [])]
        c_depends = [expand(src_path, x) for x in flags.pop('c_depends', [])]
        if not have_cython:
            pyx = '%s.c' % pyx[:-4]
        f_depends = [x for x in depends if x.rsplit('.', 1)[-1] in (
            'c', 'cpp', 'm')]
        module_name = get_modulename_from_file(pyx)
        flags_clean = {'depends': depends}
        for key, value in flags.items():
            if len(value):
                flags_clean[key] = value
        ext_modules.append(CythonExtension(
            module_name, [pyx] + f_depends + c_depends, **flags_clean))
    return ext_modules

print(sources)
ext_modules = get_extensions_from_sources(sources)

# -----------------------------------------------------------------------------
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


install_requires = ['ruamel.yaml>=0.10,<0.11',
                    'mpf>={}'.format(mpf_version),
                    ]

if platform == 'win32':
    install_requires += ['pypiwin32',
                         'kivy.deps.sdl2==0.1.17',
                         'kivy.deps.sdl2_dev==0.1.17',
                         'kivy.deps.glew==0.1.9',
                         'kivy.deps.gstreamer==0.1.12',
                         'kivy==1.9.1',
                         ]

# -----------------------------------------------------------------------------
# automatically detect package files
package_files = dict(mpfmc=list())
for root, subFolders, files in walk('mpfmc'):
    for fn in files:
        ext = fn.split('.')[-1].lower()
        if ext not in PACKAGE_FILES_ALLOWED_EXT:
            continue

        filename = join(root, fn)
        directory = dirname(filename)
        package_files['mpfmc'].append('/'.join(filename.split(os.sep)[1:]))

# -----------------------------------------------------------------------------
# setup !
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

    url='http://missionpinball.org',
    author='The Mission Pinball Framework Team',
    author_email='brian@missionpinball.org',
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
    ext_modules=ext_modules,

    packages=['mpfmc',],
    package_dir={'mpfmc': 'mpfmc'},
    package_data=package_files,
    zip_safe=False,

    install_requires=install_requires,

    tests_require=[],

    entry_points="""
    [mpf.config_player]
    sound_player=mpfmc.config_players.plugins.sound_player:register_with_mpf
    widget_player=mpfmc.config_players.plugins.widget_player:register_with_mpf
    slide_player=mpfmc.config_players.plugins.slide_player:register_with_mpf

    [mpf.command]
    mc=mpfmc.commands.mc:get_command
    """,
    setup_requires=['cython>=' + MIN_CYTHON_STRING] if not skip_cython else [])
