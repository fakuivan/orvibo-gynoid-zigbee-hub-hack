#!/bin/sh
mkdir /tmp/logs
pkill button
pkill udhcpc
pkill syslogd; syslogd -O /tmp/logs/run.log

ifconfig eth1 '172.31.112.101' netmask '255.255.255.0'

# Copy init script to tmp so that it does not block
# mnt from being unmounted. We also block so we exec
# our way out

cp /mnt/hack/init/fake_mnt.sh /tmp/fake_mnt.sh
exec /tmp/fake_mnt.sh
