#!/bin/bash

###################################
#
# PATRAMI Configuration variables
#

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

IP_REMOTE="128.105.145.186"

BASE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. ; pwd -P)
DATA_DIR=${BASE_DIR}/netrace_data/test-1

SUT_DIR=/users/lplung/pastrami
SUT_DATA_DIR=${BASE_DIR}/netrace_data/test-1

PCAP_FILE=${BASE_DIR}/scripts/pcap/plain-ipv6-64.pcap
SSH_KEY=/root/.ssh/id_rsa

mkdir -p "${DATA_DIR}"

#declare -a KERNEL=("k5.10" "k5.12" "k5.15" "k5.19" "k6.2" "k6.5" "k6.8" "k6.10" "k6.12" "k6.13" "k6.14")
#declare -a KERNEL=("k5.10" "k5.12" "k5.15" "k5.19")
#declare -a KERNEL=("k6.2" "k6.14")
declare -a KERNEL=("k5.15")


###################################


experiment () {
    local exp_name=$1
    local json_name=$2
    local exp_num=$3
    local duration=$4
    local rate=$5

    echo "Starting experiment $exp_name at rate $rate pkt/s for $exp_num times"

    exp_json="[[${rate}, 0], "

    for i in $(seq 1 $exp_num); do
        echo "Test $i"
        trex_cmd=$(python3 "${BASE_DIR}"/scripts/TrexDriverCLI4.py -s 127.0.0.1 -r ${IP_REMOTE} -c 4 -o 22 -u root --txPort 0 --rxPort 1 --rate $rate --duration $duration --pkey ${SSH_KEY} --basedir ${SUT_DIR} --datadir ${SUT_DATA_DIR} --pcap ${PCAP_FILE})
        test_cmd=$(echo $trex_cmd | xargs)

        #echo -e "#######\n$test_cmd\n#####"

        tx_pkt=$(echo "$test_cmd" | grep 'tx_packets:' | awk '{print $15}')
        rx_pkt=$(echo "$test_cmd" | grep 'rx_packets:' | awk '{print $17}')
        dr_ratio=$(echo "$test_cmd" | grep 'tx_rate:' | awk '{print $19}')
        cpu_load=$(echo "$test_cmd" | grep 'mean_cpu_load:' | awk '{print $44}')
        cpu_load_std_dev=$(echo "$test_cmd" | grep 'std_dev_cpu_load:' | awk '{print $46}')
        cpu_load_rnd_id=$(echo "$test_cmd" | grep 'random_id:' | awk '{print $48}')

        #tx_pkt=$(echo $test_cmd | awk '{print $41}')  # Trasmitted packets
        #rx_pkt=$(echo $test_cmd | awk '{print $43}')  # Received packets
        #cpu_load=$(echo $test_cmd | awk '{print $46}')  # CPU Load
        #cpu_load_std_dev=$(echo $test_cmd | awk '{print $48}')  # CPU Standard Deviation
        #tx_pkt=$(echo $test_cmd | cut -d' ' -f28)
        #rx_pkt=$(echo $test_cmd | cut -d' ' -f30)

        #echo "#######\ntx_pkt: ${tx_pkt}\n#####"
        #echo "#######\nrx_pkt: ${rx_pkt}\n#####"

        diff_pkt=$((tx_pkt - rx_pkt))

        exp_data="[$tx_pkt, $rx_pkt, $dr_ratio, $cpu_load, $cpu_load_std_dev, \"$cpu_load_rnd_id\"], "
        exp_json="${exp_json}${exp_data}"

        #echo "$trex_cmd"
        #echo -e "tx - rx:    ${diff_pkt}"
    done

    exp_json="${exp_json::-2}]"
    echo "$exp_json" >> ${json_name}  #res250/clab_raw_50_300k_k5.15_intel_bare-metal_nic_buf_4096_irq_pf0-4_pf1-6.txt

    echo "===="
    echo -e "\n\n"
}

############################
#
# Usage:
#  experiment_run <exp_name> <min_rate_kpps> <max_rate_kpps> <step_kpps> <run> <duration> <outputfile>
#
# Example:
#  experiment_run clab_routing 200 1600 100 30 10 clab_tb3_out_30_exp_t_10_k5.6_intel_bare-metal_as-is.txt

experiment_run () {
    # Define boundary values
    local exp_name=$1
    local min_rate=$2
    local max_rate=$3
    local step=$4
    local runs=$5
    local duration=$6
    local outfile=$7

    # Create an array to hold the results
    rates=()

    # Loop from first to last with the specified step
    for (( i=min_rate; i<=max_rate; i+=step )); do
        # Multiply by 1000 and add to the array
        rates+=($((i * 1000)))
    done

    # Print the array
    echo "Testing rates: ${rates[@]}"

    for rate in ${rates[@]}; do
        # experiment <exp_name> <json_name> <exp_num> <duration> <rate>
        experiment $exp_name $outfile $runs $duration $rate
    done
}



############################
#
# *** Main function ***
#
# Usage:
#  experiment_run <exp_name> <min_rate_kpps> <max_rate_kpps> <step_kpps> <run> <duration> <outputfile>
#
# Example:
#  experiment_run clab_routing 200 1600 100 30 10 clab_tb3_out_30_exp_t_10_k5.6_intel_bare-metal_as-is.txt

for KRL in "${KERNEL[@]}"
do
   EXPCONFIG="${RUNS}_exp_t_${DURATION}_${KRL}_${NIC}_${NODE}"

   echo "Experiments configuration: ${EXPCONFIG}_date_${DATE}_ver_${VER}"

   echo "Configuring SUT node"

   echo "Switching kernel to version ${KRL:1}"
   KRL_FILE=$(ssh root@${IP_REMOTE} "ls /boot/vmlinuz* | grep -F ${KRL:1}")
   ssh root@${IP_REMOTE} "${SUT_DIR}/scripts/boot-kernel.sh ${KRL_FILE}"
   sleep 5

   echo "Reboot SUT"
   ssh root@${IP_REMOTE} "reboot"

   echo "We wait 5 minutes for the SUT to come back up"
   sleep 300

   echo "Inizialiting SUT node"
   ssh root@${IP_REMOTE} "${SUT_DIR}/scripts/sut_init.sh"
   sleep 5

   echo "Show the kernel version"
   ssh root@${IP_REMOTE} "uname -a"

   echo "Wait 30 seconds before start"
   sleep 30

   echo "Starting experiment: ${EXPCOONFIG}"
   experiment_run ${NAME} ${START} ${STOP} ${STEP} ${RUNS} ${DURATION} ${DATA_DIR}/${SRV}_${TESTBED}_raw_${EXPCONFIG}_nic_buf_4096_irq_pf0-4_pf1-4_date_${DATE}_ver_${VER}.txt
done

sleep 2
echo "End of experiments."
