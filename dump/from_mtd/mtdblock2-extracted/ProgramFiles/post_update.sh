echo "run post update $1"

need_reboot=no

ip_addr=`flash get IP_ADDR`
if [ "x${ip_addr:8}" != 'x0.0.0.0' ]; then
    flash set IP_ADDR 0.0.0.0
    flash set DEF_IP_ADDR 0.0.0.0
    need_reboot=yes
fi

if [ -f /mnt/device-manager.db ] && [ ! -f /mnt/device_manager.db ]; then
    mv /mnt/device-manager.db /mnt/device_manager.db
fi

rm -f /mnt/logs/*.tar

if [ "x$need_reboot" == "xyes" ]; then
    sysled_fastblink.sh &
    sleep 30
    normal_reboot
fi
