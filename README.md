Mission Pinball Framework Media Controller (mpf_mc)
===================================================

<img align="right" height="128" src="mc/icons/128x128.png"/>

This package is for the "Media Controller" for the Mission Pinball Framework (MPF).

The architecture of MPF breaks the pinball software into two pieces. The core engine which
controls the pinball machine and runs the game logic is in the MPF package.

Separate from that is the Media Controller which controls the display and sound,
including the DMD, Color DMD, RGB LED DMD, and/or onscreen or LCD display.

This package (mpf_mc) is MPF's "default" media controller which is based on Kivy and Python.
There's also another media controller option based on Unity 3D you can use instead.

MPF_MC can run on Windows, OS X, and Linux. It can run on the same machine as
the core MPF engine, or it can be a separate machine.

More details about MPF are here : https://missionpinball.com/mpf/

[![Coverage Status](https://coveralls.io/repos/missionpinball/mpf_mc/badge.svg?branch=dev&service=github)](https://coveralls.io/github/missionpinball/mpf_mc?branch=dev)
[![Build Status](https://travis-ci.org/missionpinball/mpf_mc.svg?branch=dev)](https://travis-ci.org/missionpinball/mpf_mc)

Installation, Documentation, and Examples
-----------------------------------------

* Getting started tutorial : https://missionpinball.com/tutorial
* Installation : https://missionpinball.com/docs/installing-mpf
* User documentation : https://missionpinball.com/docs/ ([PDF](https://missionpinball.com/mpf/pdf))
* API documentation : http://missionpinball.github.io/mpf_mc/

Support
-------
We have an active online user support forum at : https://missionpinball.com/forum/mpf-users

Contributing
------------
We love pull requests! There's also a developer forum at : https://missionpinball.com/forum/mpf-dev

There's a list of authors in the AUTHORS file.

License
-------
* MPF and the MPF_MC are released under the terms of the MIT License. Please refer to the
  LICENSE file.
* The MIT license basically means you can do anything you want with MPF, including
  using it for commercial projects. You don't have to pay us or share your changes
  if you don't want to.
