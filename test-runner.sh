#!/usr/bin/env bash
set -eu -o pipefail

export PROJECT_ROOT=/data

PYTHONPATH=. coverage run -m unittest discover -v -s gitcommonsync/tests

coverage run setup.py install

# Awful bit of munging to map coverage to the copy of the module in the project package
sed -i -e 's/[^"]*ansible_module.py/\/data\/gitcommonsync\/ansible_module.py/g' .coverage*

coverage combine -a
coverage report
