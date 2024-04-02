#!/bin/sh
iptables -A INPUT -p tcp --dport 5555 -j ACCEPT
/mnt/nettest
echo "== nettest running =="
