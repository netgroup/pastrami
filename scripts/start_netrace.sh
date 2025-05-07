#!/bin/bash

DURATION=$1
EXP_ID=$2

/root/netrace | tee cpu_load_exp_id_${EXP_ID}.txt &
LAST_PID=$!
NETRACE_PID=$((LAST_PID - 1))
echo "%%% PID: ${LAST_PID} --- ${NETRACE_PID} %%%"
sleep ${DURATION}

kill -2 ${NETRACE_PID}
