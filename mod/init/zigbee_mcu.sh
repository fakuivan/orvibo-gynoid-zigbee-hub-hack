#!/bin/sh

if ! pgrep serialgateway > /dev/null; then
  echo "Searial gateway should be running" 1>&2
  exit 1
fi
if ! [ -d /mnt/actually_mnt ] || [ -e /mnt/vihome2.db ]; then
  echo "System not set up correctly" 1>&2
  exit 1
fi

(
  cd /mnt &&
  cp ./ProgramFiles/usr/local/files/empty_datastore.db ./device_manager.db
)
# Wait until vihome starts and inits the serial port
vihomed 2> /dev/null |
  grep -m 1 -q "Serial port open failed:No such file or directory"
# Kill it twice
for _ in 0 1; do
  killall -KILL vihomed
done
echo "sys_led 0" > /proc/gpio
(
  cd /mnt &&
  rm device_manager.db kvdata.db log.db vihome2.db &&
  rm -f log.db-journal
)