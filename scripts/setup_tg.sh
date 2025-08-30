#!/bin/bash

apt update
apt install -y python3-pip sysstat

pip3 install pyaml numpy paramiko

# Network Config
# --------------------------
# تعریف اینترفیس‌ها
IFACE1="enp6s0f0"
IFACE2="enp6s0f1"

# IPv6 آدرس‌ها (تو میتونی تغییر بدی به چیزی که نیاز داری)
IPV6_ADDR1="2001:db8:10::1/64"
IPV6_ADDR2="2001:db8:20::1/64"

# MAC to be set
MAC1="00:00:00:00:11:11"
MAC2="00:00:00:00:22:22"

echo "[INFO] configuration of IP and MAC"

# Bring interfaces down
ip link set $IFACE1 down
ip link set $IFACE2 down

# change MAC
ip link set dev $IFACE1 address $MAC1
ip link set dev $IFACE2 address $MAC2

# Bring interfaces up
ip link set $IFACE1 up
ip link set $IFACE2 up

# Assign IPv6
ip -6 addr flush dev $IFACE1
ip -6 addr flush dev $IFACE2
ip -6 addr add $IPV6_ADDR1 dev $IFACE1
ip -6 addr add $IPV6_ADDR2 dev $IFACE2

# ipv6 routing up
sysctl -w net.ipv6.conf.all.disable_ipv6=0
sysctl -w net.ipv6.conf.default.disable_ipv6=0

# show the output of config to make sure
echo "[INFO] config done"
ip -6 addr show $IFACE1
ip -6 addr show $IFACE2

./trex_installer.sh 3.06

cp -v trex_cfg.yaml /etc/

