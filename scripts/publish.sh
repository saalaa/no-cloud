#!/bin/sh -e

python setup.py sdist upload
python setup.py bdist_egg upload
python setup.py bdist_wheel upload

scripts/cleanup.sh
