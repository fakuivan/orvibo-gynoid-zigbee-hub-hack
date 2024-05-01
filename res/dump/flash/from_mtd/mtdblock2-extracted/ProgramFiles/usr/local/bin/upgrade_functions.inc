#!/bin/sh 

VIHOME_FIRM=/tmp/vihome.rpk
ZIGBEE_FIRM=/tmp/zigbee.bin
SYSTEM_FIRM=/tmp/system.bin
DATABASE_FIRM=/tmp/device-desc.db

# SYS_LED 闪烁
led_blink_async()
{
    sysled 2
}

# SYS_LED 灭
led_off() {
    sysled 0
}

# 停止 vihomed 进程
kill_vihome() {
    /etc/init.d/vihomed stop
}

# 启动 vihomed 进程
start_vihome() {
    /etc/init.d/vihomed start
}

post_update() {
    # 执行升级后处理脚本
    POST_UPDATE=/mnt/ProgramFiles/post_update.sh
    if [ -f $POST_UPDATE ]; then
        $POST_UPDATE $1
    fi
}

# 更新安装包文件
# 必须确保/tmp/vihome.rpk存在且通过md5sum校验
update_vihome() {
    led_blink_async
    TMP_DIR=/mnt/upgrade-tmp-dir/

    if [ -e $TMP_DIR ]; then
        rm -rf $TMP_DIR
    fi 

    try_count=0
    has_done='no'
    while [ "x$has_done" != 'xyes' ] ; do
        try_count=$(($try_count+1))
        if [ $try_count -gt 5 ]; then
            echo "tar fail for 5 times, quit"
            break
        fi
        mkdir -p $TMP_DIR
        echo "INFO: Start install vihome.rpk"
        # 先解压到临时目录
        tar xf $VIHOME_FIRM -C$TMP_DIR
        if [ $? -eq 0 ]; then
            # 成功了，就替换原来的文件
            # 这个过程不能断电，否则就会出异常
            SUM=$(md5sum ${TMP_DIR}ProgramFiles/usr/local/bin/vihomed | awk '{print $1}')
            if [ ! -f ${TMP_DIR}ProgramFiles/usr/local/files/vihomed.md5 ]; then
                echo "WARN: ${TMP_DIR}ProgramFiles/usr/local/files/vihomed.md5 not exist"
                MD5=$SUM
            else
                MD5=$(cat ${TMP_DIR}ProgramFiles/usr/local/files/vihomed.md5)
            fi
            echo "$MD5,$SUM"
            if [ "x$SUM" != "x$MD5" ];then
                echo "WARN: UPGRADE VIHOME FAILDED, ROLLBACK..."
                has_done='yes'
            else
                echo "WARN: DON'T POWER OFF !!!!"
                rm -rf /mnt/ProgramFiles
                mv ${TMP_DIR}ProgramFiles /mnt/
                echo "INFO: DONE"
                post_update vihome
                has_done='yes'
            fi
        fi
        rm -rf $TMP_DIR
    done

    led_off
}

# 更新 Zigbee 模块固件
update_zigbee() {
    led_blink_async

    try_count=0
    while true; do
        JennicModuleProgrammer \
            -s /dev/ttyS1 \
            -f $ZIGBEE_FIRM | tee /tmp/zigbee.log
        sleep 1

        IsSuccess=$(grep 'Success' /tmp/zigbee.log)
        if [ "x$IsSuccess" = 'xSuccess' ] ; then
            break;
        fi

        sleep 3
        try_count=$(($try_count+1))
        if [ $try_count -gt 3 ]; then
            echo 'JennicModuleProgrammer fail for many times, quit'
            cp /tmp/zigbee.log /mnt/zigbee.log
            break
        fi
        echo "JennicModuleProgrammer fail for $try_count, try again"
    done

    rm /tmp/zigbee.log
    led_off
}

# 更新系统固件
# 必须确保/tmp/system.bin存在且通过md5sum校验
update_system() {
    led_blink_async

    try_count=0

    while true; do
        firmware_upgrade "$SYSTEM_FIRM"
        ret=$?

        if [ $ret -eq 100 ] ; then
            fast_reboot
        fi

        try_count=$(($try_count+1))
        if [ $try_count -ge 5 ];then
            echo 'firmware_upgrade fail for many times, quit'
            break
        fi
        echo "firmware_upgrade fail for $try_count, try again"
    done

    led_off
}
