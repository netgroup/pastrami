#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, csv, time, os  # stdlib imports
# Add TRex interactive API and Scapy shipped with TRex to sys.path
sys.path.insert(0, "/opt/trex/v3.06/automation/trex_control_plane/interactive")  # TRex STL API path
sys.path.insert(0, "/opt/trex/v3.06/external_libs/scapy-2.4.3")                  # Scapy path (offline)

from trex_stl_lib.api import *                   # TRex STL objects
from scapy.all import Ether, Raw                 # Scapy L2 only

# --------------------
# Test parameters
# --------------------
SRC_MAC = "00:00:00:00:11:11"  # L2 source MAC address
DST_MAC = "00:00:00:00:22:22"  # L2 destination MAC address
ETH_TYPE = 0x88B5              # Experimental EtherType (not IP) – safe for L2-only tests

TX_PORT = 0    # TRex TX port index
RX_PORT = 1    # TRex RX port index
PGID    = 5    # Latency flow-stat group id

ITERATIONS = 7                                   # Number of repeated runs per (burst, pps)
BURSTS     = [1000, 10000, 100000]               # Total packets for single-burst mode
PPS_LIST   = [100, 1000, 10000]                  # Packets-per-second rates

CSV_FILE = "trex_iter_results_1500B_L2only.csv"  # Results CSV path

# ---- Packet sizing: exact 1500B on wire (1496B L2 + 4B FCS) ----
TARGET_WIRE_BYTES = 1500                          # Desired frame size on the wire
FCS_BYTES         = 4                             # Ethernet FCS (added by NIC)
TARGET_L2_BYTES   = TARGET_WIRE_BYTES - FCS_BYTES # 1496 bytes at L2 (without FCS)
ETHER_HDR         = 14                            # Ethernet header size w/o FCS

# Payload so that L2 length becomes exactly 1496B: 1496 - 14 = 1482
PAYLOAD_SIZE = TARGET_L2_BYTES - ETHER_HDR
if PAYLOAD_SIZE < 0:
    raise RuntimeError("Negative payload size! Check header sizes.")  # Sanity guard
PAYLOAD = b'X' * PAYLOAD_SIZE                    # Raw payload bytes (1482B)

def build_pkt():
    """Build a pure L2 Ethernet frame (no IP/UDP) with exact L2 size TARGET_L2_BYTES."""
    scapy_pkt = (
        Ether(src=SRC_MAC, dst=DST_MAC, type=ETH_TYPE) /  # 14B Ethernet header + custom EtherType
        Raw(PAYLOAD)                                      # Fill payload to reach 1496B at L2
    )
    # Scapy len() returns L2 length excluding FCS; expect TARGET_L2_BYTES for 1500B on wire.
    l2_len = len(scapy_pkt)
    if l2_len != TARGET_L2_BYTES:
        raise RuntimeError("L2 length is {} bytes, expected {} for {}B-on-wire.".format(
            l2_len, TARGET_L2_BYTES, TARGET_WIRE_BYTES))
    return STLPktBuilder(pkt=scapy_pkt)                   # Wrap for TRex

def ensure_csv_header(path):
    """Create CSV file and header row if not present."""
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
    Run one iteration. If expected duration < 1s, use continuous mode and pass
    duration=1.0 to c.start() so latency sampler has time to populate non-zero stats.
    """
    pkt_builder = build_pkt()

    expected = (burst / float(pps)) if pps > 0 else 0.0   # Expected run time in seconds
    short_run = expected < 1.0                            # Too short for latency stats?

    if short_run:
        mode = STLTXCont(pps=pps)                         # Continuous mode (no duration here)
        mode_desc = "CONT 1s"
        eff_duration = 1.0
    else:
        mode = STLTXSingleBurst(total_pkts=burst, pps=pps) # Original single-burst
        mode_desc = "SINGLE"
        eff_duration = expected

    s = STLStream(
        name="lat",                                       # Stream name
        packet=pkt_builder,                               # Packet builder
        flow_stats=STLFlowLatencyStats(pg_id=PGID),       # Enable latency stats with pg_id
        mode=mode                                         # Selected TX mode
    )

    c.reset(ports=[TX_PORT, RX_PORT])                     # Clear old streams
    c.add_streams(s, ports=[TX_PORT])                     # Add stream to TX
    c.clear_stats()                                       # Reset counters

    print("[iter {}] start -> burst={} pps={} mode={} (≈{:.2f}s)".format(
        iteration_idx, burst, pps, mode_desc, eff_duration))

    # Start traffic. For short runs we pass duration=1.0 so TRex stops automatically.
    if short_run:
        c.start(ports=[TX_PORT], duration=1.0)            # Continuous but auto-stop after 1s
    else:
        c.start(ports=[TX_PORT])                          # Single-burst run

    # Wait long enough (> 2x duration + 2s)
    wait_sec = max(10, int(eff_duration * 2) + 2)
    c.wait_on_traffic(ports=[TX_PORT], timeout=wait_sec)

    # Fetch per-pgid stats (flow + latency)
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

    print("[iter {}] TX:{} RX:{} AVG:{:.1f}us MIN:{:.1f}us MAX:{:.1f}us JIT:{:.1f}us".format(
        iteration_idx, tx_pkts, rx_pkts, avg_us, min_us, max_us, jitter_us
    ))
    return row

def main():
    """Main entry: iterate over (burst, pps), run iterations, append to CSV."""
    ensure_csv_header(CSV_FILE)

    c = STLClient()
    c.connect()
    try:
        with open(CSV_FILE, "a", newline="") as f:
            w = csv.writer(f)
            for burst in BURSTS:
                for pps in PPS_LIST:
                    print("="*60)
                    print("Experiment -> BURST={}  PPS={}".format(burst, pps))
                    print("="*60)
                    for it in range(1, ITERATIONS+1):
                        row = one_iteration(c, pps, burst, it)
                        w.writerow([
                            row["timestamp"], row["iteration"], row["pps"], row["burst"],
                            row["tx_pkts"], row["rx_pkts"],
                            row["tx_bps_l1"], row["rx_bps_l1"],
                            "{:.3f}".format(row["avg_latency_us"]),
                            "{:.3f}".format(row["min_latency_us"]),
                            "{:.3f}".format(row["max_latency_us"]),
                            "{:.3f}".format(row["jitter_us"]),
                            row["drops"], row["ooo"], row["dup"],
                            row["seq_too_high"], row["seq_too_low"]
                        ])
                        time.sleep(0.5)
    finally:
        c.disconnect()
    print("\nAll done. CSV -> {}".format(CSV_FILE))

if __name__ == "__main__":
    main()

