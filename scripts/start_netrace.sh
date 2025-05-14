#!/bin/bash

DURATION=$1
FILE_PATH=$2

BASE_PATH=$(cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P)

"${BASE_PATH}/netrace" | tee "${FILE_PATH}" &
LAST_PID=$!
NETRACE_PID=$((LAST_PID - 1))
echo "%%% PID: ${LAST_PID} --- ${NETRACE_PID} %%%"
sleep ${DURATION}

kill -2 ${NETRACE_PID}
