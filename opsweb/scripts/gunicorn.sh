#!/bin/bash
# 脚本功能: 用于管理 gunicorn 进程 - start/stop/restart/status

NAME='wsops'
DJANGODIR='/ops-data/zp/haha/mysite-11/opsweb'
USER=root
GROUP=root
NUM_WORKERS=4

# reload the application server for each request
MAX_REQUESTS=100000

# which settings file should Django use
DJANGO_SETTINGS_MODULE=opsweb.settings

# WSGI module name
DJANGO_WSGI_MODULE=opsweb.wsgi

# Activate the virtual environment
cd $DJANGODIR
source /ops-data/zp/haha/mysite-11/bin/activate

export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
export PYTHONPATH=$DJANGODIR:$PYTHONPATH
echo
echo "python 版本为: `python --version`"
echo

# Start your Django Unicorn
# Programs meant to be run under supervisor should not daemonize themselves (do not use –daemon)

function USAGE {
    echo -e "\033[31m脚本名称: \033[37m"
    echo "    $0"
    echo -e "\033[31m语法结构: \033[37m"
    echo "    $0 {start|stop|restart|status}"
    echo -e "\033[31m使用范例: \033[37m"
    echo "    $0 restart"
    echo -e "\033[31m注意事项: \033[37m"
    echo "    1. \$1(操作类型)参数必须存在"
    echo
    echo
    exit 1
}

function GETPID {
    PID=`ps aux | awk '$0~/gunicorn/&&$0~/master/&&$0!~/awk/{print $2}'`
}

function START {

    GETPID
    if [[ $PID != "" ]];then
        echo
        echo "gunicorn 进程已经存在，PID: ${PID}"
        echo
    else
        /ops-data/zp/haha/mysite-11/bin/gunicorn ${DJANGO_WSGI_MODULE}:application \
        -n ${NAME} \
        -w 4 \
        --reload \
        --max-requests ${MAX_REQUESTS} \
        --user ${USER} \
        --group ${GROUP} \
        -b 127.0.0.1:10086 \
        --log-level=error \
        --log-file=/ops-data/zp/haha/mysite-11/opsweb/logs/gunicorn.log \
        -D

        sleep 2
        GETPID
        echo
        echo "gunicorn 进程已经启动，PID: ${PID}"
        echo
    fi
}

function STOP {

    GETPID
    if [[ $PID != "" ]];then
        echo "gunicorn 进程停止中......"
        kill -9 ${PID}
        sleep 5
        echo
        echo "gunicorn 进程已被kill，kill 掉的 PID: ${PID}"
        echo
    else
        echo
        echo "gunicorn 进程不存在,不需要 stop"
        echo
    fi
}

function STATUS {
    GETPID
    if [[ $PID != "" ]];then
        echo
        echo "gunicorn 进程正在运行中，PID: ${PID}"
        echo
    else
        echo
        echo "gunicorn 进程已停止，如需启动请 start "
        echo
    fi
}

case $1 in

    start)
        START
        ;;

    stop)
        STOP
        ;;

    restart)
        STOP
        START
        ;;

    status)
        STATUS
        ;;

    *)
        USAGE
        exit
        ;;
esac
