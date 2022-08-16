Running MPF-MC Tests
====================

The exact commands you use to run the tests vary depending on whether you have installed MPF to your system or whether
you are running tests from an mpf development folder.

If you installed MPF-MC (via pip, etc.)
------------------------------------
If you installed MPF-MC to your system (for example, `pip install mpf-mc`), then you can run the tests from the
installed package via the following command:

`python -m unittest discover mpf`

This tells the unittest module to "discover" the tests in the installed mpf module. (Note that this will run all the
tests from the install mpf namespace, which will be tests from the mpf, mpf-mc, and any other mpf packages you have
installed.)

You can also run single tests via:

`python -m unittest mpf.mc.tests.test_YamlInterface`

If you want to run tests from an mpf development folder
-------------------------------------------------------
If you're actively developing MPF, then you probably installed MPF in "editable" mode (via pip install -e) which means
the system installation of MPF just contains pointers back to your development folder rather than copying files to
Python's site-packages folder.

In this case, you need to run tests from your development folder. To do this, you must run the tests from the root
repository folder. (e.g. the parent folder called "mpf-mc" which itself has a child folder called "mpfmc" in it.) Then from
there, run:

`python -m unittest discover mpfmc/tests`

If you want to run a single test, you can run it via:

`python -m unittest mpfmc.tests.test_AudioDefaultSettings`

Even with the single test, it's important that you run it from the root mpf-mc folder (which then tests in the child
mpfmc/tests folder.)
