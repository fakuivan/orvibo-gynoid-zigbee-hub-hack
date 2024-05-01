#!/bin/sh
###########################################################
# File : upgrade_by_local-rtl8196x.sh
# 
# 从 /tmp/ 目录下读取对应的文件，并执行相应的升级函数。
#
# 先确保 /tmp/ 下有 vihome.rpk, zigbee.bin, root.bin 文件
# 之一
# 
# Change Logs:
# Date          Author          Note
# 2015-08-31    Sid Lee         创建
###########################################################
source upgrade_functions.inc

main() {
    if [ -f $VIHOME_FIRM ]; then
        update_vihome 
    fi

    if [ -f $ZIGBEE_FIRM ]; then
        update_zigbee
    fi 

    if [ -f $SYSTEM_FIRM ]; then
        update_system
    fi
}

###########################################################
kill_vihome
main
start_vihome
