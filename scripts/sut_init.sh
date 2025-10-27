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

# =============================
# IPv6 Forwarding
# =============================
echo "[1/8] Enabling IPv6 forwarding..."
sysctl -w net.ipv6.conf.all.forwarding=1 >/dev/null

# =============================
# Disable NIC Offloading
# =============================
echo "[2/8] Disabling NIC offloading features..."
for IFACE in ${IN_ETH} ${OUT_ETH}; do
  ethtool -K $IFACE gro off gso off tso off lro off rx off tx off
done

# =============================
# Configure NIC ring buffer
# =============================
echo "[3/8] Setting ring buffer sizes..."
ethtool -G ${IN_ETH} rx ${IN_BUFFER} tx ${IN_BUFFER}
ethtool -G ${OUT_ETH} rx ${OUT_BUFFER} tx ${OUT_BUFFER}

# =============================
# IRQ settings
# =============================
echo "[4/8] Disabling IRQ balance..."
systemctl stop irqbalance >/dev/null 2>&1 || true

echo "[5/8] Assigning IRQs to CPU 4..."
/proj/superfluidity-PG0/pastrami/scripts/handle_nic_irq_clab-k5.6.sh 4 4 4 4

# =============================
# Set MAC addresses
# =============================
echo "[6/8] Setting MAC addresses..."
ip link set ${IN_ETH} address ${IN_MAC}
ip link set ${OUT_ETH} address ${OUT_MAC}

# =============================
# Bring interfaces up
# =============================
echo "[7/8] Bringing interfaces up..."
ip link set ${IN_ETH} up
ip link set ${OUT_ETH} up

# =============================
# Create bridge
# =============================
echo "[8/8] Setting up bridge br0..."
if ! ip link show br0 &>/dev/null; then
  echo "Creating bridge br0..."
  ip link add name br0 type bridge
else
  echo "Bridge br0 already exists. Skipping creation."
fi

# Attach interfaces to bridge
ip link set ${IN_ETH} master br0
ip link set ${OUT_ETH} master br0

# Bring bridge and member interfaces up
ip link set br0 up
ip link set ${IN_ETH} up
ip link set ${OUT_ETH} up

# =============================
# IPv6 Routing & Neighbour Setup
# =============================
echo "Configuring IPv6 routing..."
ip -6 route add ${IP_DEST} dev ${OUT_ETH} 2>/dev/null || true
sleep 1

echo "Configuring IPv6 neighbour..."
ip -6 neigh add ${IP_DEST} lladdr ${REMOTE_MAC} dev ${OUT_ETH} 2>/dev/null || true
sleep 1

echo "✅ SUT configuration complete."
