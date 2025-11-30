#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, csv, time, os
# Add TRex interactive API and Scapy shipped with TRex to sys.path
sys.path.insert(0, "/opt/v3.06/automation/trex_control_plane/interactive")  # TRex STL API path
sys.path.insert(0, "/opt/v3.06/external_libs/scapy-2.4.3")                  # Scapy path (offline)

from trex_stl_lib.api import *            # TRex STL objects
from scapy.all import Ether, Raw          # L2 only

# --------------------
# Default parameters (will be replaced if macs.csv exists)
# --------------------
SRC_MAC = "00:00:00:00:11:11"             # Default L2 source MAC
DST_MAC = "00:00:00:00:22:22"             # Default L2 destination MAC
ETH_TYPE = 0x88B5                         # Experimental EtherType (non-IP)

TX_PORT = 0                               # TRex TX port index
RX_PORT = 1                               # TRex RX port index
PGID    = 5                               # Latency flow-stat group id

ITERATIONS = 7
BURSTS     = [1000, 10000, 100000]
PPS_LIST   = [100, 1000, 10000]

CSV_FILE  = "trex_iter_results_1500B_L2only.csv"  # Output results CSV
MACS_CSV  = "macs.csv"                            # Input MACs CSV (from mac_to_csv.sh)

# ---- Exact 1500B on the wire: 1496B L2 + 4B FCS ----
TARGET_WIRE_BYTES = 1500
FCS_BYTES         = 4
TARGET_L2_BYTES   = TARGET_WIRE_BYTES - FCS_BYTES  # 1496 bytes at L2
ETHER_HDR         = 14                              # Ethernet header (no FCS)

# Payload such that L2 length is exactly 1496: 1496 - 14 = 1482
PAYLOAD_SIZE = TARGET_L2_BYTES - ETHER_HDR
if PAYLOAD_SIZE < 0:
    raise RuntimeError("Negative payload size! Check header sizes.")
PAYLOAD = b'X' * PAYLOAD_SIZE                      # 1482B payload


# ------------------------------------------------------
# Helper: read MAC addresses automatically from macs.csv
# ------------------------------------------------------
def read_macs_from_csv(path):
    """
    Read TX/RX MAC addresses from macs.csv created by mac_to_csv.sh.

    Expected CSV header:
      PCI_Address,MAC_Address,Driver

    Selection logic:
      - If any row has PCI ending with '.0' → use its MAC for TX
      - If any row has PCI ending with '.1' → use its MAC for RX
      - Otherwise, fallback to the first two rows as TX then RX
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"MAC CSV not found: {path}")

    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))

    if len(rows) < 2:
        raise ValueError("MAC CSV must have at least two rows.")

    mac_tx = mac_rx = None
    for r in rows:
        pci = (r.get("PCI_Address") or "").strip()
        mac = (r.get("MAC_Address") or "").strip()
        if pci.endswith(".0") and not mac_tx:
            mac_tx = mac
        if pci.endswith(".1") and not mac_rx:
            mac_rx = mac

    # Fallback to first two rows if '.0' / '.1' not present
    if not mac_tx or not mac_rx:
        mac_tx = mac_tx or (rows[0].get("MAC_Address") or "").strip()
        mac_rx = mac_rx or (rows[1].get("MAC_Address") or "").strip()

    if not mac_tx or not mac_rx:
        raise ValueError(f"Could not parse MACs from CSV: tx='{mac_tx}' rx='{mac_rx}'")

    return mac_tx, mac_rx


# ------------------------------------------------------
# Packet builder
# ------------------------------------------------------
def build_pkt():
    """Build a pure L2 Ethernet frame with exact L2 size of 1496 bytes (no FCS)."""
    scapy_pkt = (
        Ether(src=SRC_MAC, dst=DST_MAC, type=ETH_TYPE) /  # 14B header + EtherType
        Raw(PAYLOAD)                                      # 1482B payload → total L2 = 1496
    )
    l2_len = len(scapy_pkt)  # Scapy length excludes FCS
    if l2_len != TARGET_L2_BYTES:
        raise RuntimeError("L2 length is {} bytes, expected {} for {}B-on-wire."
                           .format(l2_len, TARGET_L2_BYTES, TARGET_WIRE_BYTES))
    return STLPktBuilder(pkt=scapy_pkt)


def ensure_csv_header(path):
    """Create the results CSV and write the header if file does not exist."""
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow([
                "timestamp", "iteration", "pps", "burst",
                "tx_pkts", "rx_pkts",
                "tx_bps_l1", "rx_bps_l1",
                "avg_latency_us", "min_latency_us",
                "max_latency_us", "jitter_us",
                "drops", "ooo", "dup", "seq_too_high", "seq_too_low"
            ])


def one_iteration(c, pps, burst, iteration_idx):
    """
    Run exactly one iteration for the given (pps, burst).
    If expected duration < 1s, switch to continuous mode (duration=1s) so the
    latency sampler has enough time to produce non-zero stats.
    """
    pkt_builder = build_pkt()

    expected = (burst / float(pps)) if pps > 0 else 0.0
    short_run = expected < 1.0

    if short_run:
        mode = STLTXCont(pps=pps)              # Continuous mode (stop via duration)
        mode_desc = "CONT 1s"
        eff_duration = 1.0
    else:
        mode = STLTXSingleBurst(total_pkts=burst, pps=pps)
        mode_desc = "SINGLE"
        eff_duration = expected

    s = STLStream(
        name="lat",
        packet=pkt_builder,
        flow_stats=STLFlowLatencyStats(pg_id=PGID),
        mode=mode
    )

    c.reset(ports=[TX_PORT, RX_PORT])
    c.add_streams(s, ports=[TX_PORT])
    c.clear_stats()

    print(f"[iter {iteration_idx}] start -> burst={burst} pps={pps} mode={mode_desc} (≈{eff_duration:.2f}s)")

    if short_run:
        c.start(ports=[TX_PORT], duration=1.0)  # auto-stop after 1s
    else:
        c.start(ports=[TX_PORT])                # single-burst stops itself

    wait_sec = max(10, int(eff_duration * 2) + 2)
    c.wait_on_traffic(ports=[TX_PORT], timeout=wait_sec)

    # Per-PGID stats (flow + latency)
    pgids = c.get_active_pgids()
    stats = c.get_pgid_stats(pgids['latency'])

    flow = stats['flow_stats'].get(PGID, {})
    latg = stats['latency'].get(PGID, {})
    errc = latg.get('err_cntrs', {})

    tx_pkts   = flow.get('tx_pkts', {}).get(TX_PORT, 0)
    rx_pkts   = flow.get('rx_pkts', {}).get(RX_PORT, 0)
    tx_bps_l1 = flow.get('tx_bps_l1', {}).get(TX_PORT, 0)
    rx_bps_l1 = flow.get('rx_bps_l1', {}).get(RX_PORT, 0)

    lat       = latg.get('latency', {})
    avg_us    = lat.get('average', 0.0)
    min_us    = lat.get('total_min', 0.0)
    max_us    = lat.get('total_max', 0.0)
    jitter_us = lat.get('jitter', 0.0)

    row = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "iteration": iteration_idx,
        "pps": pps,
        "burst": burst,
        "tx_pkts": tx_pkts,
        "rx_pkts": rx_pkts,
        "tx_bps_l1": tx_bps_l1,
        "rx_bps_l1": rx_bps_l1,
        "avg_latency_us": avg_us,
        "min_latency_us": min_us,
        "max_latency_us": max_us,
        "jitter_us": jitter_us,
        "drops": errc.get('dropped', 0),
        "ooo": errc.get('out_of_order', 0),
        "dup": errc.get('dup', 0),
        "seq_too_high": errc.get('seq_too_high', 0),
        "seq_too_low": errc.get('seq_too_low', 0),
    }

    print(f"[iter {iteration_idx}] TX:{tx_pkts} RX:{rx_pkts} "
          f"AVG:{avg_us:.1f}us MIN:{min_us:.1f}us MAX:{max_us:.1f}us JIT:{jitter_us:.1f}us")
    return row


def main():
    """Main entry: read MACs, iterate over (burst, pps), run iterations, append to CSV."""
    global SRC_MAC, DST_MAC

    # 1) Read MACs from macs.csv in the current directory
    macs_csv_path = os.path.join(os.getcwd(), MACS_CSV)
    try:
        mac_tx, mac_rx = read_macs_from_csv(macs_csv_path)
        SRC_MAC, DST_MAC = mac_tx, mac_rx
        print(f"Using MACs from '{macs_csv_path}': SRC(TX)={SRC_MAC}  DST(RX)={DST_MAC}")
    except Exception as e:
        print(f"[WARN] Could not read '{macs_csv_path}' -> using default MACs. Reason: {e}")

    # 2) Ensure results CSV header exists
    ensure_csv_header(CSV_FILE)

    # 3) Run experiments
    c = STLClient()
    c.connect()
    try:
        with open(CSV_FILE, "a", newline="") as f:
            w = csv.writer(f)
            for burst in BURSTS:
                for pps in PPS_LIST:
                    print("=" * 60)
                    print(f"Experiment -> BURST={burst}  PPS={pps}")
                    print("=" * 60)
                    for it in range(1, ITERATIONS + 1):
                        row = one_iteration(c, pps, burst, it)
                        w.writerow([
                            row["timestamp"], row["iteration"], row["pps"], row["burst"],
                            row["tx_pkts"], row["rx_pkts"],
                            row["tx_bps_l1"], row["rx_bps_l1"],
                            f"{row['avg_latency_us']:.3f}",
                            f"{row['min_latency_us']:.3f}",
                            f"{row['max_latency_us']:.3f}",
                            f"{row['jitter_us']:.3f}",
                            row["drops"], row["ooo"], row["dup"],
                            row["seq_too_high"], row["seq_too_low"]
                        ])
                        time.sleep(0.5)
    finally:
        c.disconnect()

    print(f"\nAll done. CSV -> {CSV_FILE}")


if __name__ == "__main__":
    main()
