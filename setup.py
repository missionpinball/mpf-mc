"""Mission Pinball Framework Media Controller (mpf-mc) setup.py.

Notes:
    This setup script is a modified/customized version of the Kivy setup.py script.
"""

import sys
import re

from copy import deepcopy
import os
from os.path import join, dirname, sep, exists, isdir
from os import walk, environ
from distutils.version import LooseVersion
from distutils.sysconfig import get_python_inc
from collections import OrderedDict
from time import sleep

from sysconfig import get_paths
from setuptools import setup, Extension
print('Using setuptools')


# fix error with py3's LooseVersion comparisons
def ver_equal(self, other):
    return self.version == other


LooseVersion.__eq__ = ver_equal


MIN_CYTHON_STRING = '0.24'
MIN_CYTHON_VERSION = LooseVersion(MIN_CYTHON_STRING)
MAX_CYTHON_STRING = '0.29.21'
MAX_CYTHON_VERSION = LooseVersion(MAX_CYTHON_STRING)
CYTHON_UNSUPPORTED = (
    # ref https://github.com/cython/cython/issues/1968
    '0.27', '0.27.2'
)
CYTHON_REQUIRES_STRING = (
    'cython>={min_version},<={max_version},{exclusion}'.format(
        min_version=MIN_CYTHON_STRING,
        max_version=MAX_CYTHON_STRING,
        exclusion=','.join('!=%s' % excl for excl in CYTHON_UNSUPPORTED),
    )
)

PACKAGE_FILES_ALLOWED_EXT = ('py', 'yaml', 'png', 'md', 'zip', 'gif', 'jpg',
                             'mp4', 'm4v', 'so', 'pyd', 'dylib', 'wav', 'ogg',
                             'pxd', 'pyx', 'c', 'h', 'ttf', 'fnt', 'txt')

on_rtd = os.environ.get('READTHEDOCS') == 'True'


def getoutput(cmd, env=None):
    # pylint: disable-msg=import-outside-toplevel
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
    pconfig = join(sys.prefix, 'libs', 'pkgconfig')

    if isdir(pconfig):
        lenviron = environ.copy()
        lenviron['PKG_CONFIG_PATH'] = '{};{}'.format(
            environ.get('PKG_CONFIG_PATH', ''), pconfig)
    cmd = 'pkg-config --libs --cflags {}'.format(' '.join(packages))
    results = getoutput(cmd, lenviron).split()
    for token in results:
        extension = token[:2].decode('utf-8')
        flag = flag_map.get(extension)
        if not flag:
            continue
        kw.setdefault(flag, []).append(token[2:].decode('utf-8'))
    return kw


def get_isolated_env_paths():
    try:
        # sdl2_dev is installed before setup.py is run, when installing from
        # source due to pyproject.toml. However, it is installed to a
        # pip isolated env, which we need to add to compiler
        # pylint: disable-msg=import-outside-toplevel
        import kivy_deps.sdl2_dev as sdl2_dev
    except ImportError:
        return [], []

    sdl_root = os.path.abspath(join(sdl2_dev.__path__[0], '../../../..'))
    includes = [join(sdl_root, 'Include')] if isdir(join(sdl_root, 'Include')) else []
    libs = [join(sdl_root, 'libs')] if isdir(join(sdl_root, 'libs')) else []
    return includes, libs


# -----------------------------------------------------------------------------
# Determine on which platform we are

platform = sys.platform

# Detect 32/64bit for OSX (http://stackoverflow.com/a/1405971/798575)
if sys.platform == 'darwin':
    if sys.maxsize > 2 ** 32:
        osx_arch = 'x86_64'
    else:
        osx_arch = 'i386'

# Detect Python for android project (http://github.com/kivy/python-for-android)
ndkplatform = environ.get('NDKPLATFORM')
if ndkplatform is not None and environ.get('LIBLINK'):
    platform = 'android'
kivy_ios_root = environ.get('KIVYIOSROOT', None)
if kivy_ios_root is not None:
    platform = 'ios'
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
c_options['use_sdl2'] = True
c_options['use_gstreamer'] = True
c_options['use_avfoundation'] = platform == 'darwin'
c_options['use_osx_frameworks'] = platform == 'darwin'

# now check if environ is changing the default values
for key in list(c_options.keys()):
    ukey = key.upper()
    if ukey in environ:
        value = bool(int(environ[ukey]))
        print('Environ change {0} -> {1}'.format(key, value))
        c_options[key] = value


# -----------------------------------------------------------------------------
# Cython check
# Cython usage is optional (.c files are included to build without Cython)
#
cython_unsupported_append = '''

  Please note that the following versions of Cython are not supported
  at all: {}
'''.format(', '.join(map(str, CYTHON_UNSUPPORTED)))

cython_min = '''\
  This version of Cython is not compatible with MPF-MC. Please upgrade to
  at least version {0}, preferably the newest supported version {1}.

  If your platform provides a Cython package, make sure you have upgraded
  to the newest version. If the newest version available is still too low,
  please remove it and install the newest supported Cython via pip:

    pip install -I Cython=={1}{2}\
'''.format(MIN_CYTHON_STRING, MAX_CYTHON_STRING,
           cython_unsupported_append if CYTHON_UNSUPPORTED else '')

cython_max = '''\
  This version of Cython is untested with MPF-MC. While this version may
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
skip_cython = environ.get('USE_CYTHON', False) not in ['1', 'True', 'TRUE', 'true', 'Yes', 'YES', 'y', 'Y']

if skip_cython:
    print("\nSkipping Cython build (using .c files)")
else:
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
        print("\nCython is missing and the USE_CYTHON environment variable is set to True!\n\n")
        raise

if not have_cython:
    from distutils.command.build_ext import build_ext   # noqa

# -----------------------------------------------------------------------------
# Setup classes

# the build path where kivy is being compiled
src_path = build_path = dirname(__file__)


class CustomBuildExt(build_ext):

    def finalize_options(self):
        # pylint: disable-msg=assignment-from-no-return
        retval = build_ext.finalize_options(self)
        global build_path   # noqa
        if (self.build_lib is not None and exists(self.build_lib) and
                not self.inplace):
            build_path = self.build_lib
        return retval

    def build_extensions(self):
        c = self.compiler.compiler_type
        print('Detected compiler is {}'.format(c))
        if c != 'msvc':
            for e in self.extensions:
                e.extra_link_args += ['-lm']

        build_ext.build_extensions(self)


def _check_and_fix_sdl2_mixer(f_path_to_check):
    # Between SDL_mixer 2.0.1 and 2.0.4, the included frameworks changed
    # smpeg2 have been replaced with mpg123, but there is no need to fix.
    smpeg2_path = ("{}/Versions/A/Frameworks/smpeg2.framework"
                   "/Versions/A/smpeg2").format(f_path_to_check)
    if not exists(smpeg2_path):
        return

    print("Check if SDL2_mixer smpeg2 have an @executable_path")
    rpath_from = ("@executable_path/../Frameworks/SDL2.framework"
                  "/Versions/A/SDL2")
    rpath_to = "@rpath/../../../../SDL2.framework/Versions/A/SDL2"
    output = getoutput(("otool -L '{}'").format(smpeg2_path)).decode('utf-8')
    if "@executable_path" not in output:
        return

    print("WARNING: Your SDL2_mixer version is invalid")
    print("WARNING: The smpeg2 framework embedded in SDL2_mixer contains a")
    print("WARNING: reference to @executable_path that will fail the")
    print("WARNING: execution of your application.")
    print("WARNING: We are going to change:")
    print("WARNING: from: {}".format(rpath_from))
    print("WARNING: to: {}".format(rpath_to))
    getoutput("install_name_tool -change {} {} {}".format(
        rpath_from, rpath_to, smpeg2_path))

    output = getoutput(("otool -L '{}'").format(smpeg2_path))
    if b"@executable_path" not in output:
        print("WARNING: Change successfully applied!")
        print("WARNING: You'll never see this message again.")
    else:
        print("WARNING: Unable to apply the changes, sorry.")


gst_flags = {}

if platform == 'darwin':
    if c_options['use_osx_frameworks']:
        if osx_arch == "i386":
            print("Warning: building with frameworks fail on i386")
        else:
            print("OSX framework used, force to x86_64 only")
            environ["ARCHFLAGS"] = environ.get("ARCHFLAGS", "-arch x86_64")
            print("OSX ARCHFLAGS are: {}".format(environ["ARCHFLAGS"]))

# detect gstreamer, only on desktop
# works if we forced the options or in autodetection
if c_options['use_gstreamer'] in (None, True):
    gstreamer_valid = False
    if c_options['use_osx_frameworks'] and platform == 'darwin':
        # check the existence of frameworks
        f_path = '/Library/Frameworks/GStreamer.framework'
        if not exists(f_path):
            c_options['use_gstreamer'] = False
            print('GStreamer framework not found, fallback on pkg-config')
        else:
            print('GStreamer framework found')
            gstreamer_valid = True
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
    elif platform == 'win32':
        gst_flags = pkgconfig('gstreamer-1.0')
        if 'libraries' in gst_flags:
            print('GStreamer found via pkg-config')
            gstreamer_valid = True
            c_options['use_gstreamer'] = True
        else:
            _includes = get_isolated_env_paths()[0] + [get_paths()['include']]
            for include_dir in _includes:
                if exists(join(include_dir, 'gst', 'gst.h')):
                    print('GStreamer found via gst.h')
                    gstreamer_valid = True
                    c_options['use_gstreamer'] = True
                    gst_flags = {
                        'libraries':
                            ['gstreamer-1.0', 'glib-2.0', 'gobject-2.0']}
                    break

    if not gstreamer_valid:
        # use pkg-config approach instead
        gst_flags = pkgconfig('gstreamer-1.0')
        if 'libraries' in gst_flags:
            print('GStreamer found via pkg-config')
            gstreamer_valid = True
            c_options['use_gstreamer'] = True

    if not gstreamer_valid:
        raise RuntimeError('GStreamer not found and is required to build MPF-MC')

# detect SDL2
# works if we forced the options or in autodetection
sdl2_flags = {}
if c_options['use_sdl2'] in (None, True):
    sdl2_valid = False
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
        for name in ('SDL2', 'SDL2_image', 'SDL2_mixer'):
            f_path = '/Library/Frameworks/{}.framework'.format(name)
            if not exists(f_path):
                print('Missing framework {}'.format(f_path))
                sdl2_valid = False
                continue
            sdl2_flags['extra_link_args'] += ['-framework', name]
            sdl2_flags['include_dirs'] += [join(f_path, 'Headers')]
            print('Found sdl2 frameworks: {}'.format(f_path))
            if name == 'SDL2_mixer':
                _check_and_fix_sdl2_mixer(f_path)

        if not sdl2_valid:
            c_options['use_sdl2'] = False
            print('SDL2 frameworks not found, fallback on pkg-config')
        else:
            c_options['use_sdl2'] = True
            print('Activate SDL2 compilation')

    if not sdl2_valid and platform != "ios":
        # use pkg-config approach instead
        sdl2_flags = pkgconfig('sdl2', 'SDL2_image', 'SDL2_mixer')
        if 'libraries' in sdl2_flags:
            print('SDL2 found via pkg-config')
            c_options['use_sdl2'] = True

# -----------------------------------------------------------------------------
# declare flags


def get_modulename_from_file(filename_to_check):
    filename_to_check = filename_to_check.replace(sep, '/')
    pyx = '.'.join(filename_to_check.split('.')[:-1])
    pyxl = pyx.split('/')
    while pyxl[0] != 'mpfmc':
        pyxl.pop(0)
    if pyxl[1] == 'mpfmc':
        pyxl.pop(0)
    return '.'.join(pyxl)


def expand(root_path, *args):
    return join(root_path, 'mpfmc', *args)


class CythonExtension(Extension):

    def __init__(self, *args, **kwargs):
        Extension.__init__(self, *args, **kwargs)
        self.cython_directives = {
            'c_string_encoding': 'utf-8',
            'profile': 'USE_PROFILE' in environ,
            'embedsignature': environ.get('USE_EMBEDSIGNATURE', '0') == 1,
            'language_level': 3,
            'unraisable_tracebacks': True}
        # XXX with pip, setuptools is imported before distutils, and change
        # our pyx to c, then, cythonize doesn't happen. So force again our
        # sources
        self.sources = args[1]


def merge(d1, *args):
    d1 = deepcopy(d1)
    for d2 in args:
        for item_key, item_value in d2.items():
            item_value = deepcopy(item_value)
            if item_key in d1:
                d1[item_key].extend(item_value)
            else:
                d1[item_key] = item_value
    return d1


def determine_base_flags():
    flags = {
        'libraries': [],
        'include_dirs': [join(src_path, 'kivy', 'include')],
        'library_dirs': [],
        'extra_link_args': [],
        'extra_compile_args': []}
    if platform.startswith('freebsd'):
        flags['include_dirs'] += [join(
            environ.get('LOCALBASE', '/usr/local'), 'include')]
        flags['library_dirs'] += [join(
            environ.get('LOCALBASE', '/usr/local'), 'lib')]
    elif platform == 'darwin':
        v = os.uname()
        if v[2] >= '13.0.0':
            # use xcode-select to search on the right Xcode path
            # XXX use the best SDK available instead of a specific one
            # pylint: disable-msg=import-outside-toplevel
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
    elif platform == 'win32':
        flags['include_dirs'] += [get_python_inc(prefix=sys.prefix)]
        flags['library_dirs'] += [join(sys.prefix, "libs")]
    return flags


def determine_sdl2():
    flags = {}
    if not c_options['use_sdl2']:
        return flags

    sdl2_path = environ.get('KIVY_SDL2_PATH', None)

    if sdl2_flags and not sdl2_path and platform == 'darwin':
        return sdl2_flags

    includes, _ = get_isolated_env_paths()

    # no pkgconfig info, or we want to use a specific sdl2 path, so perform
    # manual configuration
    flags['libraries'] = ['SDL2', 'SDL2_image', 'SDL2_mixer']
    split_chr = ';' if platform == 'win32' else ':'
    sdl2_paths = sdl2_path.split(split_chr) if sdl2_path else []

    if not sdl2_paths:
        sdl2_paths = []
        for include in includes + [join(sys.prefix, 'include')]:
            sdl_inc = join(include, 'SDL2')
            if isdir(sdl_inc):
                sdl2_paths.append(sdl_inc)
        sdl2_paths.extend(['/usr/local/include/SDL2', '/usr/include/SDL2'])

    flags['include_dirs'] = sdl2_paths
    flags['extra_link_args'] = []
    flags['extra_compile_args'] = []
    flags['library_dirs'] = (
        sdl2_paths if sdl2_paths else
        ['/usr/local/lib/'])

    if sdl2_flags:
        flags = merge(flags, sdl2_flags)

    # ensure headers for all the SDL2 and sub libraries are available
    libs_to_check = ['SDL', 'SDL_mixer', 'SDL_image']
    can_compile = True
    for lib in libs_to_check:
        found = False
        for d in flags['include_dirs']:
            inc_dir = join(d, '{}.h'.format(lib))
            if exists(inc_dir):
                found = True
                print('SDL2: found {} header at {}'.format(lib, inc_dir))
                break

        if not found:
            print('SDL2: missing sub library {}'.format(lib))
            can_compile = False

    if not can_compile:
        c_options['use_sdl2'] = False
        return {}

    return flags


base_flags = determine_base_flags()

# -----------------------------------------------------------------------------
# sources to compile
sources = {
    'core/audio/sound_file.pyx': {
        'depends': ['core/audio/sdl2_helper.h', 'core/audio/gstreamer_helper.h']},
    'core/audio/track.pyx': {
        'depends': ['core/audio/sdl2_helper.h', 'core/audio/gstreamer_helper.h']},
    'core/audio/track_standard.pyx': {
        'depends': ['core/audio/sdl2_helper.h', 'core/audio/gstreamer_helper.h']},
    'core/audio/track_sound_loop.pyx': {
        'depends': ['core/audio/sdl2_helper.h', 'core/audio/gstreamer_helper.h']},
    'core/audio/audio_interface.pyx': {
        'depends': ['core/audio/sdl2_helper.h', 'core/audio/gstreamer_helper.h']},
    'core/audio/playlist_controller.pyx': {},
    'uix/bitmap_font/bitmap_font.pyx': {'depends': ['core/audio/sdl2.pxi', ]}
}

if c_options["use_sdl2"] and not on_rtd:
    sdl2_flags = determine_sdl2()
else:
    sdl2_flags = {}

if sdl2_flags:
    for source_file, depends in sources.items():
        sources[source_file] = merge(
            base_flags, gst_flags, sdl2_flags, depends)


# -----------------------------------------------------------------------------
# extension modules

def get_extensions_from_sources(sources_to_search):
    ext_modules_found = []
    for pyx, flags in sources_to_search.items():
        pyx = expand(src_path, pyx)
        depends_sources = [expand(src_path, x) for x in flags.pop('depends', [])]
        c_depends = [expand(src_path, x) for x in flags.pop('c_depends', [])]
        if not have_cython:
            pyx = '%s.c' % pyx[:-4]
        f_depends = [x for x in depends_sources if x.rsplit('.', 1)[-1] in (
            'c', 'cpp', 'm')]
        module_name = get_modulename_from_file(pyx)
        flags_clean = {'depends': depends_sources}
        for item_key, item_value in flags.items():
            if item_value:
                flags_clean[item_key] = item_value
        ext_modules_found.append(CythonExtension(
            module_name, [pyx] + f_depends + c_depends, **flags_clean))
    return ext_modules_found


print(sources)

if not on_rtd:
    ext_modules = get_extensions_from_sources(sources)
else:
    ext_modules = []

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

install_requires = ['ruamel.yaml==0.15.100',  # better YAML library
                    'mpf>={}'.format(mpf_version),
                    'kivy==2.0.0',
                    'psutil==5.7.3',
                    'Pygments==2.6.1',  # YAML syntax formatting for the iMC
                    # also update those in appveyor.yaml if you change versions
                    'kivy_deps.sdl2==0.3.1;platform_system=="Windows"',
                    'kivy_deps.sdl2-dev==0.3.1;platform_system=="Windows"',
                    'kivy_deps.glew==0.3.0;platform_system=="Windows"',
                    'kivy_deps.glew-dev==0.3.0;platform_system=="Windows"',
                    'kivy_deps.gstreamer==0.3.1;platform_system=="Windows"',
                    'kivy_deps.gstreamer-dev==0.3.1;platform_system=="Windows"',
                    'ffpyplayer==4.3.2'
                    ]

# If we're running on Read The Docs, then we just need to copy the files
# (since mpf-docs uses the test YAML files in the doc build), and we don't
# need to actually install mpf-mc, so override the installation requirements:

if on_rtd:
    install_requires = []

# -----------------------------------------------------------------------------
# automatically detect package files
package_files = dict(mpfmc=list())
for root, _, files in walk('mpfmc'):
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
    author='The Mission Pinball Framework Team',
    author_email='brian@missionpinball.org',
    url='http://missionpinball.org',
    license='MIT',
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
    keywords='pinball',
    ext_modules=ext_modules,
    cmdclass={'build_ext': CustomBuildExt},
    packages=['mpfmc'],
    package_dir={'mpfmc': 'mpfmc'},
    package_data=package_files,
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Topic :: Artistic Software',
        'Topic :: Games/Entertainment :: Arcade'
    ],
    install_requires=install_requires,
    tests_require=[],
    entry_points='''
    [mpf.config_player]
    sound_player=mpfmc.config_players.plugins.sound_player:register_with_mpf
    sound_loop_player=mpfmc.config_players.plugins.sound_loop_player:register_with_mpf
    playlist_player=mpfmc.config_players.plugins.playlist_player:register_with_mpf
    widget_player=mpfmc.config_players.plugins.widget_player:register_with_mpf
    slide_player=mpfmc.config_players.plugins.slide_player:register_with_mpf
    track_player=mpfmc.config_players.plugins.track_player:register_with_mpf
    display_light_player=mpfmc.config_players.plugins.display_light_player:register_with_mpf

    [mpf.command]
    mc=mpfmc.commands.mc:get_command
    imc=mpfmc.commands.imc:get_command
    ''',
    setup_requires=[CYTHON_REQUIRES_STRING] if not skip_cython else [])
