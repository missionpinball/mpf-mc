#!/bin/bash

# run from root of repo

set -ex

if [ ! -d mpfmc ]; then
    echo "must run from root of repo"
    exit 1
fi


# Check to see if Homebrew is installed, and install it if it is not
command -v brew >/dev/null 2>&1 || { echo >&2 "Installing Homebrew Now"; \
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install)"; }

brew update
brew install SDL2 SDL2_mixer SDL2_image SDL2_ttf gstreamer
brew upgrade SDL2 SDL2_mixer SDL2_image SDL2_ttf gstreamer

which -a python3
which python3
python3 -m pip install --upgrade pip
python3 -m pip install --upgrade setuptools wheel build twine

# python3 -m pip uninstall mpf mpf-mc
# python3 -m pip install -e ../mpf
# python3 -m pip install -e .

python3 -m build
python3 -m twine upload dist/*.whl -u __token__