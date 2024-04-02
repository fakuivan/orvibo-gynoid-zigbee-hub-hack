#!/bin/sh

DATABASE=/mnt/log.db

CREATE_DB="CREATE TABLE log (utc_time INTEGER NOT NULL,local_time DATETIME NOT NULL,grade TEXT NOT NULL,type TINYINT NOT NULL,context TEXT NOT NULL);"

if [ 2 -le $# ]; then
	#生成SQL语句
	level=$1
	if [ "ERROR" = $level ]; then
		sql="INSERT INTO log values ($(date +%s),datetime('now','localtime'),'ERROR',3,'$2');"
	elif [ "WARNING" = $level ]; then
		sql="INSERT INTO log values ($(date +%s),datetime('now','localtime'),' WARN',4,'$2');"
	elif [ "INFO" = $level ]; then
		sql="INSERT INTO log values ($(date +%s),datetime('now','localtime'),' INFO',6,'$2');"
	else
		sql="INSERT INTO log values ($(date +%s),datetime('now','localtime'),'DEBUG',7,'$2');"
	fi

	#判断是否指定路径
	if [ $3 ]; then
		DATABASE=$3
	fi

	#判断数据库是否存在
	if [ ! -f $DATABASE ]; then
		echo $CREATE_DB | sqlite3 $DATABASE
	fi

	echo $sql | sqlite3 $DATABASE

else
	echo "?? you need to input 2 params[level(ERROR,WARNING,INFO,DEBUG(other)),logstring,[dbpath]]"
fi
