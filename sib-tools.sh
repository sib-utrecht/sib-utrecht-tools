#!/bin/sh

set -e

PYTHONPATH="$PWD/member-admin:$PYTHONPATH" \
  python -m sib_tools "$@"
