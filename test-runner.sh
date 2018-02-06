#!/usr/bin/env bash
set -eu -o pipefail

export PYTHON_COVERAGE=1
PYTHONPATH=. coverage run -m unittest discover -v -s gitcommonsync/tests

coverage run setup.py install

coverage combine -a
coverage report
