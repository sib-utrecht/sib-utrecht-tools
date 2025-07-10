#!/bin/sh

TMP_OUT=$(mktemp)
journalctl --user -u sib-tools-listen-email "$@" 2>&1 | tee "$TMP_OUT"
if grep -qE 'Unit sib-tools-listen-email.service could not be found.|-- No entries --' "$TMP_OUT"; then
    echo "Unit not found or no entries in user session, trying system session..."
    journalctl -u sib-tools-listen-email "$@"
fi
rm -f "$TMP_OUT"

