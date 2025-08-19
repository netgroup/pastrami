#!/bin/bash

TREX_DIR="/opt/trex/v3.06"
TEST_SCRIPT="rtt_64byte_solveitteration_ipv6.py"
# اجرای TRex اگر ران نیست
pgrep t-rex-64 > /dev/null || {
    cd $TREX_DIR
    sudo nohup ./t-rex-64 -i -c 1 --iom 0 --software > /tmp/trex.log 2>&1 &
    echo "TRex started"
    sleep 10
}

# اجرای اسکریپت تست
cd ~/pastrami/scripts
python3 $TEST_SCRIPT

