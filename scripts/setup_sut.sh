#!/bin/bash

echo "SUT node setup..."
apt update
apt install -y python3-pip sysstat
pip3 install numpy


echo "Configuring SUT node"
./sut_init.sh
