#!/bin/sh
set -eu

python -m compileall -q src tests
python -m unittest discover -s tests -v
python -m ada doctor
