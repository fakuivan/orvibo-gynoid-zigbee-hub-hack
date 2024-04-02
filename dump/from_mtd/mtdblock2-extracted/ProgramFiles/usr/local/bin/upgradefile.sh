#!/bin/sh 
###############################################################################
# File: upgradefile.sh
#
# 从URL下载升级文件，并升级软件
# 
# ./upgradefile.sh -t <TYPE> -u <URL> -m <MD5SUM>
# - TYPE 升级类型：5-vihomed; 1-zigbee; 6-system
# - URL  升级文件资源路径
# - MD5SUM  md5sum校验码
#
# Change Logs:
# Date          Author          Note
# 2015-07-16    Bingo           Create
# 2015-08-29    Sid Lee         集成到MiniHub，添加描述
# 2015-08-31    Sid Lee         将升级函数独立到 upgrade_functions.inc
###############################################################################

source upgrade_functions.inc

sendsignaltovihome() {
	vihomedPid=$(cat /tmp/vihomed.pid)
    kill -66 $vihomedPid
    sleep 4
}

# 0:成功, 1:失败
vihomed_upgrade() {
    wget -O $VIHOME_FIRM $URL
    if [ -e $VIHOME_FIRM ]; then
        SUM=$(md5sum $VIHOME_FIRM | awk '{print $1}')
        if [ "x$SUM" == "x$MD5" ];then
            sendsignaltovihome
            kill_vihome
            update_vihome
            rm $VIHOME_FIRM
            start_vihome
            return 0
        else
            echo "check md5sum fail!"
            rm $VIHOME_FIRM
            return 1
        fi
    else
        echo "file $VIHOME_FIRM not exist!"
        return 1
    fi
}

# 0:成功, 1:失败
zigbee_upgrade() {
    wget -O $ZIGBEE_FIRM $URL
    if [ -e $ZIGBEE_FIRM ];then
        SUM=$(md5sum $ZIGBEE_FIRM | awk '{print $1}')
        if [ "x$SUM" == "x$MD5" ];then
            sendsignaltovihome
            kill_vihome
            update_zigbee
            sleep 3
            rm $ZIGBEE_FIRM
            start_vihome
            return 0
        else
            echo "check md5sum fail!"
            rm $ZIGBEE_FIRM
            return 1
        fi
    else
        echo "file $ZIGBEE_FIRM NOT EXIST!"
        return 1
    fi
}

# 0:成功, 1:失败
system_update()
{
    wget -O $SYSTEM_FIRM $URL
    if [ -e $SYSTEM_FIRM ];then
        SUM=$(md5sum $SYSTEM_FIRM | awk '{print $1}')
        if [ "x$SUM" == "x$MD5" ];then
            sendsignaltovihome
            kill_vihome
            update_system
            rm $SYSTEM_FIRM
            start_vihome
            return 0
        fi
    else
        echo "file $SYSTEM_FIRM NOT EXIST!"
    fi
    return 1
}

# 0:成功, 1:失败
database_update()
{
    wget -O $DATABASE_FIRM $URL
    if [ -e $DATABASE_FIRM ];then
        SUM=$(md5sum $DATABASE_FIRM | awk '{print $1}')
        if [ "x$SUM" == "x$MD5" ];then
            mv $DATABASE_FIRM /usr/local/files/device-desc.db
            return 0
        fi
    else
        echo "file $DATABASE_FIRM NOT EXIST!"
    fi
    return 1
}

###########################################################
while getopts "t:u:m:" opt; do
    case $opt in
    t)TYPE=$OPTARG
    echo "type=$TYPE"
    ;;
    u)URL=$OPTARG
    echo "url=$URL"
    ;;
    m)MD5=$OPTARG
    echo "md5=$MD5"
    ;;
    \?)
    echo "Invalid option:-$OPARG"
    exit 1
    ;;
    esac
done

case $TYPE in
    5) upgrade_func=vihomed_upgrade;;
    1) upgrade_func=zigbee_upgrade;;
    6) upgrade_func=system_update;;
    8) upgrade_func=database_update;;
    *) return 1;;
esac
echo "upgrade_func=$upgrade_func"

try_count=0
$upgrade_func
while ! [ $? -eq 0 ]; do
    try_count=$(($try_count+1))
    if [ $try_count -ge 10 ]; then
        echo "upgrade fail, quit"
        return 1
    fi
    echo "upgrade fail, try again $try_count"
    $upgrade_func
done

exit 0
