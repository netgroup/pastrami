#!/bin/bash

# Base directory (current working directory)
WORKDIR=$(pwd)
CONFIG_FILE="$WORKDIR/latency_config.yaml"
TREX_DIR="/opt/v3.06"

# Read selected test name from YAML
TEST_SCRIPT=$(awk -F': ' '/^selected_test:/{gsub(/"/,"",$2); print $2}' "$CONFIG_FILE")

if [[ -z "$TEST_SCRIPT" ]]; then
  echo "❌ No test selected in $CONFIG_FILE"
  exit 1
fi

echo "==> Selected test: $TEST_SCRIPT"
echo "==> Working directory: $WORKDIR"

# Start TRex if not running
pgrep -f t-rex-64 > /dev/null || {
    cd "$TREX_DIR"
    sudo nohup ./t-rex-64 -i -c 1 --iom 0 --software > /tmp/trex.log 2>&1 &
    echo "TRex started"
    sleep 10
}

# Run the selected Python test from current directory
cd "$WORKDIR"
python3 "$WORKDIR/$TEST_SCRIPT.py"
