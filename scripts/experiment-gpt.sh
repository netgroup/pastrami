#!/bin/bash

###################################
#
# PATRAMI Configuration variables
#

BASE_DIR=${PASTRAMI_BASE_DIR:-$(dirname "$0")}
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR="${BASE_DIR}/netrace_data/test-0"

NAME=clab_cpu
START=250
STOP=260
STEP=10
RUNS=1
DURATION=30
NIC=intel
NODE=bare-metal
SRV=clab
TESTBED=tb0
DATE=$(date -Iminutes)
VER=01
IP_REMOTE="128.105.145.228"

mkdir -p "${DIR}"

declare -a KERNEL=("k5.15")

###################################

experiment () {
    local exp_name=$1
    local json_name=$2
    local exp_num=$3
    local duration=$4
    local rate=$5

    echo "Starting experiment $exp_name at rate $rate pkt/s for $exp_num times"

    exp_json="[[${rate}, 4], "

    for i in $(seq 1 $exp_num); do
        echo "Test $i"
        result_json=$(python3 $SCRIPTS_DIR/TrexDriverCLI4_gpt_onethread.py -s 127.0.0.1 -r ${IP_REMOTE} -c 4 -o 22 -u root --txPort 0 --rxPort 1 --rate $rate --duration $duration --pkey /root/.ssh/id_rsa --pcap /proj/superfluidity-PG0/srperf2/pcap/trex-pcap-files/plain-ipv6-64.pcap)

        echo "$result_json"

        pid=$(echo "$result_json" | grep 'random_id:' | awk '{print $2}')
        duration_sec=$(echo "$result_json" | grep 'duration_sec' | awk '{print $2}')
        mean_cpu_load=$(echo "$result_json" | grep 'mean_cpu_load:' | awk '{print $2}')
        std_dev_cpu_load=$(echo "$result_json" | grep 'std_dev_cpu_load:' | awk '{print $2}')

        exp_data="[PID: $pid, duration_sec: $duration_sec, mean_cpu_load: $mean_cpu_load, std_dev_cpu_load: $std_dev_cpu_load]"
        exp_json="${exp_json}${exp_data}"
    done

    exp_json="${exp_json}]"
    echo "$exp_json" >> ${json_name}
    echo "===="
    echo -e "\n\n"
}

experiment_run () {
    local exp_name=$1
    local min_rate=$2
    local max_rate=$3
    local step=$4
    local runs=$5
    local duration=$6
    local outfile=$7

    rates=()
    for (( i=min_rate; i<=max_rate; i+=step )); do
        rates+=($((i * 1000)))
    done

    echo "Testing rates: ${rates[@]}"

    for rate in ${rates[@]}; do
        experiment $exp_name $outfile $runs $duration $rate
    done
}

for KRL in "${KERNEL[@]}"
do
   EXPCONFIG="${RUNS}_exp_t_${DURATION}_${KRL}_${NIC}_${NODE}"

   echo "Experiments configuration: ${EXPCONFIG}_date_${DATE}_ver_${VER}"

   echo "Configuring SUT node"
   echo "Switching kernel to version ${KRL:1}"
   KRL_FILE=$(ssh root@${IP_REMOTE} "ls /boot/vmlinuz* | grep -F ${KRL:1}")
   ssh root@${IP_REMOTE} "${SCRIPTS_DIR}/boot-kernel.sh ${KRL_FILE}"
   sleep 5

   echo "Inizialiting SUT node"
   ssh root@${IP_REMOTE} " ${SCRIPTS_DIR}/sut_init.sh"
   sleep 5

   echo "Show the kernel version"
   ssh root@${IP_REMOTE} "uname -a"

   echo "Wait 30 seconds before start"
   sleep 5

   echo "Starting experiment: ${EXPCONFIG}"
   experiment_run ${NAME} ${START} ${STOP} ${STEP} ${RUNS} ${DURATION} ${DIR}/${SRV}_${TESTBED}_raw_${EXPCONFIG}_nic_buf_4096_irq_pf0-4_pf1-4_date_${DATE}_ver_${VER}.txt
done

sleep 2
echo "End of experiments."
