#!/bin/bash
# Script: run_all.sh
# Description: Grant execution permission to all files, then run setup_tg.sh and onecklic.py

# 1. Give execute permission to all files with extensions
chmod +x *.*

# 2. Run setup_tg.sh with sudo
echo "Running setup_tg.sh..."
sudo ./setup_tg.sh

# 3. Run onecklic.py with Python3
echo "Running onecklic.py..."
python3 oneclick.py

echo "All tasks completed successfully!"
