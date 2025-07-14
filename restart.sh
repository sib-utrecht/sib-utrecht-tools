#!/bin/sh

# These lines have been added to '/etc/sudoers':
#
# sib-tools ALL=(root) NOPASSWD: /bin/systemctl restart sib-tools-listen-email
# sib-tools ALL=(root) NOPASSWD: /bin/systemctl start sib-tools-listen-email
# sib-tools ALL=(root) NOPASSWD: /bin/systemctl stop sib-tools-listen-email
#
# This allows the non-wheel user `sib-tools` to execute the restart, start and
# stop the service.
#

sudo /bin/systemctl restart sib-tools-listen-email
