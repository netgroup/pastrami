#!/bin/bash

apt update
apt install -y python3-pip sysstat

pip3 install pyaml numpy paramiko

./trex_installer.sh 3.04

cp -v trex_cfg.yaml /etc/

