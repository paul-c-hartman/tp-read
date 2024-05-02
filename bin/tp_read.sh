#!/usr/bin/env bash
echo Untested! For now!

if command -v python3 >/dev/null ; then
	python3 ./tp_read.py "$@"
elif ! python -c 'import sys; assert sys.version_info >= (3,6)' > /dev/null; then
	python ./tp_read.py "$@"
else
	echo "Can't find python3!"
fi