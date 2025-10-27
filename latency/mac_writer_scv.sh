#!/bin/bash
# Extract TRex interface info and save to CSV in current directory

TREX_DIR="/opt/v3.06"
TREX_BIN="$TREX_DIR/t-rex-64"
OUT_FILE="$(pwd)/macs.csv"   # ذخیره در مسیر جاری

echo "==> Killing old TRex processes..."
sudo pkill -9 -f t-rex-64 2>/dev/null || true
sudo pkill -9 -f dpdk 2>/dev/null || true
sudo rm -rf /var/run/dpdk 2>/dev/null || true

echo "==> Preparing hugepages..."
sudo sysctl -w vm.nr_hugepages=1024 >/dev/null
sudo mkdir -p /mnt/huge
sudo mount -t hugetlbfs nodev /mnt/huge 2>/dev/null || true

echo
echo "==> Dumping TRex interfaces and saving as CSV..."
cd "$TREX_DIR" || exit 1

# اجرای TRex و گرفتن خطوط شامل PCI و MAC و Driver و ساخت فایل CSV در مسیر فعلی
sudo $TREX_BIN --dump-interfaces 2>/dev/null \
  | grep -E "PCI:" \
  | awk -v OFS=',' '
    BEGIN {print "PCI_Address,MAC_Address,Driver"} 
    {
      pci=$2;
      mac="";
      drv="";
      for (i=1;i<=NF;i++) {
        if ($i=="MAC:") mac=$(i+1);
        if ($i=="Driver:") drv=$(i+1);
      }
      print pci,mac,drv
    }' > "$OUT_FILE"

echo
echo "✅ Done. CSV saved at: $OUT_FILE"
echo
column -s, -t "$OUT_FILE"
echo
