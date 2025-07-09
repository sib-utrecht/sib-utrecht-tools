#!/bin/sh

set -e

PYTHONPATH="$PWD:$PYTHONPATH" \
  python -m sib_tools "$@"
