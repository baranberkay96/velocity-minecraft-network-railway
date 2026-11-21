#!/bin/sh
set -eu
mkdir -p /data
if [ "$(id -u)" = 0 ]; then
  chown 1000:1000 /data
  exec setpriv --reuid=1000 --regid=1000 --clear-groups python3 /opt/server/launch.py
fi
exec python3 /opt/server/launch.py
