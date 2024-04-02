#!/bin/sh

while true; do 
    echo "sys_led 1">/proc/gpio; 
    usleep 10000; 
    echo "sys_led 0" > /proc/gpio; 
    usleep 10000; 
done
