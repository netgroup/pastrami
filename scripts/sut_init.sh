#!/bin/bash

IN_ETH=enp6s0f0
OUT_ETH=enp6s0f1

IN_MAC=00:00:00:00:22:11
OUT_MAC=00:00:00:00:11:22
SOURCE_MAC=00:00:00:00:11:11
REMOTE_MAC=00:00:00:00:22:22

IP_DEST=b::2
IN_BUFFER=4096
OUT_BUFFER=4096


# Enabling IPv6 forwarding
echo "Enabling IPv6 forwarding"
sysctl -w net.ipv6.conf.all.forwarding=1


# Disable NIC Offloading features
echo "Disable NIC Offloading features"
ethtool -K ${IN_ETH} gro off
ethtool -K ${IN_ETH} gso off
ethtool -K ${IN_ETH} tso off
ethtool -K ${IN_ETH} lro off
ethtool -K ${IN_ETH} rx off tx off

ethtool -K ${OUT_ETH} gro off
ethtool -K ${OUT_ETH} gso off
ethtool -K ${OUT_ETH} tso off
ethtool -K ${OUT_ETH} lro off
ethtool -K ${OUT_ETH} rx off tx off


# Configurign interface ring buffer
echo "Configurign interface ring buffer"
ethtool -G ${IN_ETH} rx ${IN_BUFFER} tx ${IN_BUFFER}
ethtool -G ${OUT_ETH} rx ${OUT_BUFFER} tx ${OUT_BUFFER}


# Disable IRQ Balance
echo "Disable IRQ Balance"
systemctl stop irqbalance

# Set IRQ on CPU 4
echo "Set IRQon CPU 4"
/proj/superfluidity-PG0/pastrami/scripts/handle_nic_irq_clab-k5.6.sh 4 4 4 4


# Setting proper mac addresses
echo "Setting proper mac addresses"
ip link set ${IN_ETH} address ${IN_MAC}
ip link set ${OUT_ETH} address ${OUT_MAC}


# Bring interfaces up
echo "Bring interfaces up"
ip link set ${IN_ETH} up
ip link set ${OUT_ETH} up


# Configuring IPv6 routing
echo "Configuring IPv6 routing..."
ip -6 route add ${IP_DEST} dev ${OUT_ETH}
sleep 2


# Configuring neighbours
echo "Configuring neighbours..."
ip -6 neigh add ${IP_DEST} lladdr ${REMOTE_MAC} dev ${OUT_ETH}
sleep 2


echo "Finish SUT Configuration"
