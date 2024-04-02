# 检查进程状态，如果退出则重新启动
run_process_if_it_down()
{
    process_name=$1
    process_num=`ps | awk "/\<\${process_name}\>/ && !/awk/" | wc -l`
    start_command=$2
    if [ $process_num -eq 0 ]; then
        $start_command
    fi
}
