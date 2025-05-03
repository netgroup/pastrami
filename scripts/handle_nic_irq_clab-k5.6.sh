#!/bin/bash

set -x
set -u
set -e

readonly PF0_HANDLER_REGEX="enp6s0f0"
readonly PF1_HANDLER_REGEX="enp6s0f1"

readonly PF0_QUE_HANDLER_REGEX="enp6s0f0-TxRx-[0-9]+"
readonly PF1_QUE_HANDLER_REGEX="enp6s0f1-TxRx-[0-9]+"

#readonly VF0_HANDLER_REGEX="iavf-enp24s0f1v0np0-TxRx-[0-9]+"
#readonly VF1_HANDLER_REGEX="iavf-enp24s0f1v1np1-TxRx-[0-9]+"

#readonly VF0_MBX_HANDLER_REGEX="iavf-0000:18:0a.0:mbx"
#readonly VF1_MBX_HANDLER_REGEX="iavf-0000:18:0a.1:mbx"


get_irq_list()
{
        local hname="${1}"

         grep -E "${hname}" /proc/interrupts | awk -F ':' '{printf $1}'
}

__enforce_smp_affinity_list()
{
        local cpu_list="${1}"
        local irqnum="${2}"

        echo "${cpu_list}" > "/proc/irq/${irqnum}/smp_affinity_list"
}

set_pfx_cpu_irq_affinity()
{
        local pfx="${1}"
        local cpu="${2}"
        local irq_list

        irq_list="$(get_irq_list "${pfx}")"
        for irq in $(echo "${irq_list}"); do
                __enforce_smp_affinity_list "${cpu}" "${irq}"
        done
}

#lstopo: numa0 core 0-14 pari (1-15 dispari HT) nic intel su numa0

set_pfx_cpu_irq_affinity "${PF0_HANDLER_REGEX}" $1
set_pfx_cpu_irq_affinity "${PF1_HANDLER_REGEX}" $2

set_pfx_cpu_irq_affinity "${PF0_QUE_HANDLER_REGEX}" $3
set_pfx_cpu_irq_affinity "${PF1_QUE_HANDLER_REGEX}" $4

#set_pfx_cpu_irq_affinity "${VF0_HANDLER_REGEX}" 33
#set_pfx_cpu_irq_affinity "${VF1_HANDLER_REGEX}" 35

#set_pfx_cpu_irq_affinity "${VF0_MBX_HANDLER_REGEX}" 33
#set_pfx_cpu_irq_affinity "${VF1_MBX_HANDLER_REGEX}" 35
