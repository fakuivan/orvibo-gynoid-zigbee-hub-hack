#!/bin/sh
###############################################################################
# Copyrights (C), 2015 - 2020, Orvibo
# All rights reversed.
#
# File : vihomed_monitor.sh
#
# 监控 vihomed 进程状态，一旦发现进程退出，立即启动新进程
#
# Change Logs:
# Date          Author          Note
# 2015-06-01    Bingo           Created
# 2015-08-31    Sid Lee         移植到RTL819x平台 
###############################################################################

file_log="/mnt/monitor.log"

start_vihomed()
{
    PID_FILE=/tmp/vihomed.pid
    [ -f $PID_FILE ] && rm -f $PID_FILE

    echo "[`date`] vihomed restart for $1" >> $file_log
    /etc/init.d/vihomed start
}

check_closewait()
{
    stat=`netstat -tpn | awk '/CLOSE_WAIT/ && /vihomed/ && $5~/:10001/' | wc -l`
    if [ $stat -gt 0 ]; then
        /etc/init.d/vihomed stop
        start_vihomed 'network close wait'
    fi
}

main()
{
    vihomed_num=`ps | awk '/\<vihomed\>/ && !/awk/' | wc -l`
    if [ "$vihomed_num" -gt 0 ]; then
        check_closewait
    else
        start_vihomed 'process exit'
    fi
}

main
