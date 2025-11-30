#!/bin/bash
# =========================================================
# One-click installer for PASTRAMI TG/SUT setup
# ---------------------------------------------------------
# - Detects base directory automatically (pwd → .. → /scripts)
# - Runs TG local scripts
# - SSH to SUT and runs setup scripts
# - Launches TRex locally
# - Reads SUT IP and private key path from config.yml
# =========================================================

set -e  # Exit immediately on any error

# ----------------------------
# Detect dynamic paths
# ----------------------------
CWD="$(pwd)"                             # e.g. /users/Rmoradi/pastrami/latency
BASE_DIR="$(dirname "$CWD")"             # -> /users/Rmoradi/pastrami
SCRIPTS_DIR="$BASE_DIR/scripts"          # -> /users/Rmoradi/pastrami/scripts
CONFIG_PATH="$SCRIPTS_DIR/config.yml"    # config file path

echo "🚀 One-Click starting..."
echo "-------------------------------------------"
echo "CWD         : $CWD"
echo "BASE_DIR    : $BASE_DIR"
echo "SCRIPTS_DIR : $SCRIPTS_DIR"
echo "CONFIG_PATH : $CONFIG_PATH"
echo "-------------------------------------------"

# ----------------------------
# Check files and folders
# ----------------------------
if [[ ! -d "$SCRIPTS_DIR" ]]; then
  echo "[ERR] Scripts directory not found: $SCRIPTS_DIR"
  exit 1
fi

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "[ERR] Config file not found: $CONFIG_PATH"
  exit 1
fi

# Required scripts list
for f in rename_interface.py setup_tg.sh rename_interface_sut.py setup_sut.sh trex_run_fin.sh; do
  if [[ ! -f "$SCRIPTS_DIR/$f" ]]; then
    echo "[ERR] Missing file in /scripts/: $f"
    exit 1
  fi
done

# ----------------------------
# Parse YAML values (simple grep)
# ----------------------------
get_yaml_value() {
  local key="$1"
  grep -E "^${key}:" "$CONFIG_PATH" | sed -E "s/^[^:]+:[[:space:]]*\"?([^\"#]+)\"?.*/\1/"
}

IP_REMOTE=$(get_yaml_value "IP_REMOTE")
SUT_SSH_USER=$(get_yaml_value "SUT_SSH_USER")
PRIVATE_KEY_REL=$(get_yaml_value "PRIVATE_KEY")
SSH_PORT=$(get_yaml_value "SSH_PORT")

# Apply defaults
: "${SUT_SSH_USER:=root}"
: "${SSH_PORT:=22}"

# Resolve full path of private key (relative to /scripts)
if [[ "$PRIVATE_KEY_REL" == /* ]]; then
  PRIVATE_KEY="$PRIVATE_KEY_REL"
else
  PRIVATE_KEY="$SCRIPTS_DIR/$PRIVATE_KEY_REL"
fi

# Check config values
if [[ -z "$IP_REMOTE" ]]; then
  echo "[ERR] IP_REMOTE not set in config.yml"
  exit 1
fi
if [[ ! -f "$PRIVATE_KEY" ]]; then
  echo "[ERR] PRIVATE_KEY not found: $PRIVATE_KEY"
  exit 1
fi

# ----------------------------
# 1) TG: rename interfaces
# ----------------------------
echo "[LOCAL] rename_interface.py"
cd "$SCRIPTS_DIR"
sudo python3 rename_interface.py

# ----------------------------
# 2) TG: setup TG
# ----------------------------
echo "[LOCAL] setup_tg.sh"
sudo ./setup_tg.sh

# ----------------------------
# 3) SUT: rename interfaces (SSH)
# ----------------------------
echo "[REMOTE] rename_interface_sut.py on $SUT_SSH_USER@$IP_REMOTE"
ssh -i "$PRIVATE_KEY" -p "$SSH_PORT" -o StrictHostKeyChecking=no "$SUT_SSH_USER@$IP_REMOTE" \
  "cd $SCRIPTS_DIR && sudo python3 rename_interface_sut.py"

# ----------------------------
# 4) SUT: setup SUT (SSH)
# ----------------------------
echo "[REMOTE] setup_sut.sh on $SUT_SSH_USER@$IP_REMOTE"
ssh -i "$PRIVATE_KEY" -p "$SSH_PORT" -o StrictHostKeyChecking=no "$SUT_SSH_USER@$IP_REMOTE" \
  "cd $SCRIPTS_DIR && sudo ./setup_sut.sh"

# ----------------------------
# 5) TG: run TRex
# ----------------------------
echo "[LOCAL] trex_run_fin.sh"
sudo ./trex_run_fin.sh

echo
echo "🎉 All done successfully!"
echo "-------------------------------------------"
