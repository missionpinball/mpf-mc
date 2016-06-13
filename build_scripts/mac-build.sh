#!/usr/bin/env bash

python3 -m pip install -U setuptools wheel pip mock --retries 20 --timeout 60
pip3 install ../../mpf
cd ..
python3 -m pip install . --retries 20 --timeout 60
python3 setup.py bdist_wheel --dist-dir=build_scripts/dist
