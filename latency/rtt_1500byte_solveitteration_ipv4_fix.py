#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, csv, time, os  # stdlib imports
# Add TRex interactive API and Scapy shipped with TRex to sys.path
sys.path.insert(0, "/opt/trex/v3.06/automation/trex_control_plane/interactive")  # TRex STL API path
sys.path.insert(0, "/opt/trex/v3.06/external_libs/scapy-2.4.3")                  # Scapy path (offline)

from trex_stl_lib.api import *                   # TRex STL objects
from scapy.all import Ether, IP, UDP, Raw        # Scapy protocol layers

# --------------------
# Test parameters
# --------------------
SRC_MAC = "00:00:00:00:11:11"  # L2 source MAC address
DST_MAC = "00:00:00:00:22:22"  # L2 destination MAC address

TX_PORT = 0    # TRex TX port index
RX_PORT = 1    # TRex RX port index
PGID    = 5    # Latency flow-stat group id

ITERATIONS = 7                                   # Number of repeated runs per (burst, pps)
BURSTS     = [1000, 10000, 100000]               # Total packets for single-burst mode
PPS_LIST   = [100, 1000, 10000]                  # Packets-per-second rates

CSV_FILE = "trex_iter_results_1500B_ipv4_fix.csv"    # Results CSV path (renamed for clarity)

# ---- Packet sizing: exact 1500B on wire (1496B L2 + 4B FCS) ----
TARGET_WIRE_BYTES = 1500                         # Target frame size on the wire
FCS_BYTES         = 4                            # Ethernet FCS size (added by NIC)
TARGET_L2_BYTES   = TARGET_WIRE_BYTES - FCS_BYTES  # L2 length excluding FCS -> 1496

ETHER_HDR = 14  # Ethernet header without FCS
IP_HDR    = 20  # IPv4 header without options
UDP_HDR   = 8   # UDP header

# Payload so that L2 length becomes exactly TARGET_L2_BYTES (1496):
PAYLOAD_SIZE = TARGET_L2_BYTES - (ETHER_HDR + IP_HDR + UDP_HDR)  # 1496 - (14+20+8) = 1454
if PAYLOAD_SIZE < 0:
    raise RuntimeError("Negative payload size! Check header sizes.")  # Sanity guard
PAYLOAD = b'X' * PAYLOAD_SIZE  # Raw payload bytes (1454B)

def build_pkt():
    """Build one IPv4/UDP Ethernet frame with exact L2 size TARGET_L2_BYTES (FCS excluded)."""
    scapy_pkt = (
        Ether(src=SRC_MAC, dst=DST_MAC) /               # L2 header (14B)
        IP(src="10.10.2.1", dst="10.10.1.1") /          # L3 header (20B)
        UDP(dport=12, sport=1025) /                     # L4 header (8B)
        Raw(PAYLOAD)                                    # Raw payload (computed to fit)
    )
    # Scapy len() returns L2 length excluding FCS; expect TARGET_L2_BYTES for 1500B on wire.
    l2_len = len(scapy_pkt)                              # Compute L2 frame size
    if l2_len != TARGET_L2_BYTES:
        raise RuntimeError("L2 length is {} bytes, expected {} for {}B-on-wire.".format(
            l2_len, TARGET_L2_BYTES, TARGET_WIRE_BYTES))
    return STLPktBuilder(pkt=scapy_pkt)                  # Wrap for TRex

def ensure_csv_header(path):
    """Create CSV file and header row if not present."""
    new = not os.path.exists(path)                       # Check if file exists
    with open(path, "a", newline="") as f:               # Append mode is safe here
        w = csv.writer(f)                                 # CSV writer
        if new:
            w.writerow([                                  # Column names
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
    If expected duration < 1s, use continuous mode and pass duration=1.0 to c.start()
    so the latency sampler has time to populate non-zero stats.
    """
    pkt_builder = build_pkt()                            # Build the packet once

    expected = (burst / float(pps)) if pps > 0 else 0.0  # Expected run time in seconds
    short_run = expected < 1.0                           # Will be too short for latency stats?

    if short_run:
        mode = STLTXCont(pps=pps)                        # Continuous mode (no 'duration' param)
        mode_desc = "CONT 1s"                            # Description for logs
        eff_duration = 1.0                               # Effective duration we request on start()
    else:
        mode = STLTXSingleBurst(total_pkts=burst, pps=pps)  # Keep original single-burst
        mode_desc = "SINGLE"                                # Description for logs
        eff_duration = expected                             # Effective duration

    s = STLStream(
        name="lat",                                        # Stream name
        packet=pkt_builder,                                # Packet builder
        flow_stats=STLFlowLatencyStats(pg_id=PGID),        # Enable latency stats with pg_id
        mode=mode                                          # Selected TX mode
    )

    c.reset(ports=[TX_PORT, RX_PORT])                      # Reset ports to clear old streams
    c.add_streams(s, ports=[TX_PORT])                      # Add stream to TX port
    c.clear_stats()                                        # Reset statistics counters

    print("[iter {}] start -> burst={} pps={} mode={} (≈{:.2f}s)".format(
        iteration_idx, burst, pps, mode_desc, eff_duration))  # Human-readable preface

    # Start traffic. For short runs we pass duration=1.0 so TRex stops automatically.
    if short_run:
        c.start(ports=[TX_PORT], duration=1.0)             # Continuous but auto-stop after 1s
    else:
        c.start(ports=[TX_PORT])                           # Single-burst runs stop by themselves

    # Wait for traffic to drain; give generous timeout (> 2x duration + 2s)
    wait_sec = max(10, int(eff_duration * 2) + 2)          # Compute timeout
    c.wait_on_traffic(ports=[TX_PORT], timeout=wait_sec)    # Block until done or timeout

    # Fetch per-pgid stats (flow + latency)
    pgids = c.get_active_pgids()                            # Active pgids in this session
    stats = c.get_pgid_stats(pgids['latency'])              # Retrieve latency-related stats

    flow = stats['flow_stats'].get(PGID, {})                # Flow counters for this pgid
    latg = stats['latency'].get(PGID, {})                   # Latency group for this pgid
    errc = latg.get('err_cntrs', {})                        # Error counters

    # TX/RX packet counters and L1 bitrates (TRex computed)
    tx_pkts   = flow.get('tx_pkts', {}).get(TX_PORT, 0)     # TX packets from TX port
    rx_pkts   = flow.get('rx_pkts', {}).get(RX_PORT, 0)     # RX packets at RX port
    tx_bps_l1 = flow.get('tx_bps_l1', {}).get(TX_PORT, 0)   # L1 TX bitrate (incl. preamble+IFG)
    rx_bps_l1 = flow.get('rx_bps_l1', {}).get(RX_PORT, 0)   # L1 RX bitrate

    # Latency metrics in microseconds
    lat       = latg.get('latency', {})                     # Latency dict
    avg_us    = lat.get('average', 0.0)                     # Average latency (us)
    min_us    = lat.get('total_min', 0.0)                   # Min latency (us)
    max_us    = lat.get('total_max', 0.0)                   # Max latency (us)
    jitter_us = lat.get('jitter', 0.0)                      # Jitter (us)

    # Prepare a row for CSV/result aggregation
    row = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),    # Local timestamp
        "iteration": iteration_idx,                         # Iteration index
        "pps": pps,                                         # Configured rate
        "burst": burst,                                     # Configured burst (original value)
        "tx_pkts": tx_pkts,                                 # Measured TX packets
        "rx_pkts": rx_pkts,                                 # Measured RX packets
        "tx_bps_l1": tx_bps_l1,                             # L1 TX bitrate
        "rx_bps_l1": rx_bps_l1,                             # L1 RX bitrate
        "avg_latency_us": avg_us,                           # Avg latency
        "min_latency_us": min_us,                           # Min latency
        "max_latency_us": max_us,                           # Max latency
        "jitter_us": jitter_us,                             # Jitter
        "drops": errc.get('dropped', 0),                    # Dropped packets by analyzer
        "ooo": errc.get('out_of_order', 0),                 # Out-of-order count
        "dup": errc.get('dup', 0),                          # Duplicate sequence count
        "seq_too_high": errc.get('seq_too_high', 0),        # Seq too high errors
        "seq_too_low": errc.get('seq_too_low', 0),          # Seq too low errors
    }

    # Console summary for this iteration
    print("[iter {}] TX:{} RX:{} AVG:{:.1f}us MIN:{:.1f}us MAX:{:.1f}us JIT:{:.1f}us".format(
        iteration_idx, tx_pkts, rx_pkts, avg_us, min_us, max_us, jitter_us
    ))
    return row                                             # Return for CSV writer

def main():
    """Main entry: iterate over (burst, pps), run iterations, append to CSV."""
    ensure_csv_header(CSV_FILE)                             # Make sure CSV header exists

    c = STLClient()                                        # Create TRex client
    c.connect()                                            # Connect to TRex server
    try:
        with open(CSV_FILE, "a", newline="") as f:         # Open CSV for appending
            w = csv.writer(f)                              # CSV writer
            for burst in BURSTS:                           # For each burst size
                for pps in PPS_LIST:                       # For each pps
                    print("="*60)                          # Visual separator
                    print("Experiment -> BURST={}  PPS={}".format(burst, pps))  # Case header
                    print("="*60)                          # Visual separator
                    for it in range(1, ITERATIONS+1):      # Iterations loop (1..ITERATIONS)
                        row = one_iteration(c, pps, burst, it)  # Run one iteration
                        # Write row to CSV (format latencies to 3 decimals)
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
                        time.sleep(0.5)                    # Small gap to avoid back-to-back runs
    finally:
        c.disconnect()                                     # Always disconnect from TRex
    print("\nAll done. CSV -> {}".format(CSV_FILE))        # Final message

if __name__ == "__main__":                                  # Script entry-point
    main()                                                 # Run main

