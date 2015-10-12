#!/bin/bash
set -u

# A wrapper for easier environment setup and execution

if [ "$#" -lt 2 ]; then
	echo "Usage: $0 gdata-python-client-DIR google-sites-backup-DIR [args...]" >&2
	exit 1
fi

export PYTHONPATH="$1/src" ; shift
BINDIR="$1" ; shift

exec "$BINDIR/backup.py" "$@"
