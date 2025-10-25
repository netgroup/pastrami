#!/bin/bash

TREX_YAML_FILE_CONFIG=/etc/trex_cfg.yaml
TREX_DIR=/opt/v3.06
TREX_BIN=$TREX_DIR/t-rex-64
TREX_LOG=/tmp/trex.log

# 1. Stop any running T-Rex processes
echo "Stopping any running T-Rex instances..."
sudo pkill -f t-rex-64 || true

# 2. Setup hugepages
echo "Configuring hugepages..."
sudo sysctl -w vm.nr_hugepages=1024
sudo mkdir -p /mnt/huge
sudo mount -t hugetlbfs nodev /mnt/huge || true

# 3. Ensure trex_cfg.yaml exists
if [ ! -f "${TREX_YAML_FILE_CONFIG}" ]; then
    sudo cp ./trex_cfg.yaml "${TREX_YAML_FILE_CONFIG}"
    echo "${TREX_YAML_FILE_CONFIG} created using the default one..."
fi

# 4. Run T-Rex in background
echo "Starting T-Rex..."
cd $TREX_DIR
sudo nohup $TREX_BIN -i -c 7 --iom 0 --software > $TREX_LOG 2>&1 &
echo "T-Rex started. Logs: $TREX_LOG"
