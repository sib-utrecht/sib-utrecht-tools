#!/bin/sh

aws-vault exec vincent-laptop2-nixos-sib --duration=12h -- ./sib-tools.sh "$@"