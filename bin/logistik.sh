#!/usr/bin/env bash

LOG_DIR=/var/log/logistik

if [ $# -lt 4 ]; then
    echo "usage: $0 <home path> <environment> <port> <conda env> <log level>"
    exit 1
fi

LK_HOME=$1
LK_ENV=$2
LK_PORT=$3
LK_CONDA_ENV=$4
LK_LOG_LEVEL=$5

re='^[0-9]+$'
if ! [[ $3 =~ $re ]] ; then
   echo "error: Port a number"
   exit 1
fi

if [[ $3 -lt 1 || $3 -gt 65536 ]]; then
    echo "error: port '$3' not in range 1-65536"
    exit 1
fi

if [ ! -d $LK_HOME ]; then
    echo "error: home directory '$LK_HOME' not found"
    exit 1
fi

if [ ! -d $LOG_DIR ]; then
    if ! [ mkdir -p ${LOG_DIR} ]; then
        echo "error: could not create missing log directory '$LOG_DIR'"
        exit 1
    fi
fi

if ! cd ${LK_HOME}; then
    echo "error: could not change to home directory '$LK_HOME'"
    exit 1
fi


source ~/.bashrc
if ! which conda >/dev/null; then
    echo "error: no conda executable found"
    exit 1
fi
if ! source activate ${LK_CONDA_ENV}; then
    echo "error: could not activate conda environment $LK_CONDA_ENV"
    exit 1
fi

STATSD_HOST=$(grep STATSD_HOST ${LK_HOME}/secrets/${LK_ENV}.yaml | sed "s/.*'\(.*\)'$/\1/g")
if [[ -z "$STATSD_HOST" ]]; then
    STATSD_HOST="localhost"
fi

LOG_LEVEL=$LK_LOG_LEVEL LK_ENVIRONMENT=$LK_ENV gunicorn \
    --worker-class eventlet \
    --workers 1 \
    --threads 1 \
    --keep-alive 5 \
    --backlog 8192 \
    --timeout 120 \
    --worker-connections 100 \
    --statsd-host ${STATSD_HOST}:8125 \
    --statsd-prefix gunicorn-logistik \
    --name logistik \
    --log-file ${LOG_DIR}/gunicorn.log \
    --error-logfile ${LOG_DIR}/error.log \
    -b 0.0.0.0:$LK_PORT \
    app:app 2>&1 >> ${LOG_DIR}/logistik.log
