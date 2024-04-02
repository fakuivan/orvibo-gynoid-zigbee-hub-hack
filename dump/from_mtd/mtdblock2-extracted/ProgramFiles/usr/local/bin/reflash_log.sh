#!/bin/sh

LOG_FILE=/var/log/messages

while true; do
    echo '=== Reflash ===' > $LOG_FILE
    sleep 5
done
