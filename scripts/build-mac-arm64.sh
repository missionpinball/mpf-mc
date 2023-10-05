#!/bin/bash

# This script builds the mpf-mc package for macOS arm64
# It's done manually for now since GitHub does not have arm64 macOS runners
# It assumes Python 3.9, 3.10, and 3.11 are installed

# Run from root of repo, paste in the PyPI token when asked

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

rm -rf dist/*

# Loop through the Python versions
for version in 3.9 3.10 3.11; do
    python${version} -m pip install --upgrade pip
    python${version} -m pip install --upgrade setuptools wheel build

    yes | python${version} -m pip uninstall mpf mpf-mc
    python${version} -m pip install -e ../mpf
    python${version} -m pip install -e .
    python${version} -m build
done

python3.11 -m pip install --upgrade twine
python3.11 -m twine upload dist/*.whl -u __token__
