Mission Pinball Framework - Media Controller (mpf-mc)
=====================================================

<img align="right" height="146" src="https://missionpinball.org/images/mpfmc-logo.png"/>

This package is for the "Media Controller" for the Mission Pinball Framework (MPF).

The architecture of MPF breaks the pinball software into two pieces. The core engine which controls the pinball machine
and runs the game logic is in the MPF package. Separate from that is the Media Controller which controls the display and
sound, including the DMD, Color DMD, RGB LED DMD, and/or onscreen or LCD display. (Note that you need a media controller
to drive a DMD and sound even if you don't have an on-screen LCD window. Don't worry--you can run this headless and/or
in a console-only environment for those cases.)

This package (mpf-mc) is MPF's "in box" media controller which is based on Kivy and Python. It leverages OpenGL and the
GPU of the computer it's running on. There are other media controller projects (at various levels of completeness) you can use with MPF built on Unity, Godot, Rust, and others.

MPF-MC runs on Windows, Mac, Linux, and Raspberry Pi. It can run on the same machine as the core MPF engine, or it can be a
separate machine. It runs as a separate process from MPF, so it works well on a multi-core computer.

The MPF project homepage is here : https://missionpinball.org

[![Coverage Status](https://coveralls.io/repos/missionpinball/mpf-mc/badge.svg?branch=dev&service=github)](https://coveralls.io/github/missionpinball/mpf-mc?branch=dev)
[![Test & Build Status](https://github.com/missionpinball/mpf-mc/actions/workflows/build_wheels.yml/badge.svg)](https://github.com/missionpinball/mpf-mc/actions/workflows/build_wheels.yml)

Documentation
-------------

https://missionpinball.org

Support
-------

MPF is open source and has no official support. Some MPF users follow the MPF-users Google group: https://groups.google.com/forum/#!forum/mpf-users. Individual hardware providers may provide additional support for users of their hardware.

Contributing
------------

MPF is a passion project created and maintained by volunteers. If you're a Python coder, documentation writer, or pinball maker, feel free to make a change and submit a pull request. For more information about contributing see the [Contributing Code](https://missionpinball.org/about/contributing_to_mpf)
and [Contributing Documentation](https://missionpinball.org/about/help) pages.

License
-------

MPF and related projects are released under the MIT License. Refer to the LICENSE file for details. Docs are released under Creative Commons CC BY 4.0.
