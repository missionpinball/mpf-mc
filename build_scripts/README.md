Build Scripts for MPF-MC
========================

The build_scripts folder contains scripts for building MPF-MC (and testing those builds.) Note that
users of MPF-MC do *not* need to worry about any of this. These scripts are for people developing MPF-MC
who use them to actually build the MPF-MC Python Wheels.

Description of Files in this Folder
===================================

windows-build.bat
-----------------
Batch file you can run on a fresh Windows machine (x86 or x64) to build MPF-MC. Prereqs include:

* Python 3.4
* git
* MPF (installed with whatever version the MPF-MC you're building needs)

This script clones the mpf repo (currently hard coded with a source of z:/git/mpf), so make sure your latest
changes are committed. Then it installs Cython, mingwpy, and everything else it needs to compile the audio
interface, and it runs the setup.py in the mpf/mc/core/audio folder to build the audio interface.

Then it installs mpf-mc from the local clone of the repo, runs the unit tests, and then builds the wheel.
The wheel is then copied to the "wheels" folder under the directory the script is being run from.

The wheel will be architecture-specific (e.g. 32-bit and 64-bit Windows create different wheels.)

windows-test-wheel.bat
----------------------
Batch file which tests the installation of the mpf-mc wheel on a fresh Windows machine.

Prereqs:
* Python 3.4
* MPF (installed with the version of the mpf-mc you're testing)

This script looks for a folder called "wheels" and then installs MPF from a .whl file there. (If there
are multiple files, it will pick the one with the highest MPF version number.) After that, the script
runs the unit tests.

If the unit tests pass, we can assume we have a good wheel which can be uploaded to PyPI.
