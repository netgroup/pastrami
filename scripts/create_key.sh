#!/usr/bin/env bash
set -euo pipefail

# Simple key creator: creates <cwd>/scripts/sshkeys/tg_to_sut(.pub)
# Usage: ./create_ssh_key.sh

ROOT="$(pwd)"
KEY_DIR="$ROOT/sshkeys"
mkdir -p "$KEY_DIR"

KEY_BASE="$KEY_DIR/tg_to_sut"
if [[ -f "${KEY_BASE}" || -f "${KEY_BASE}.pub" ]]; then
  TS="$(date +%Y%m%d_%H%M%S)"
  KEY_BASE="${KEY_BASE}_$TS"
fi

ssh-keygen -t rsa -b 4096 -m PEM -f "$KEY_BASE" -N "" -C "pastrami_tg_to_sut=$(hostname)"

chmod 600 "${KEY_BASE}"
chmod 644 "${KEY_BASE}.pub"

# single concise message (Persian) with copy command
echo "key has been created: ${KEY_BASE}.pub — for adding the key to sut run the command below:"
echo "ssh root@<SUT-IP> 'mkdir -p /root/.ssh && cat >> /root/.ssh/authorized_keys' < \"${KEY_BASE}.pub\""
