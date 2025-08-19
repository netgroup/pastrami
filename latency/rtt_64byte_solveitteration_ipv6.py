#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, csv, time, os  # stdlib imports
# Add TRex interactive API and Scapy shipped with TRex to sys.path
sys.path.insert(0, "/opt/trex/v3.06/automation/trex_control_plane/interactive")  # TRex STL API path
sys.path.insert(0, "/opt/trex/v3.06/external_libs/scapy-2.4.3")                  # Scapy path (offline)

from trex_stl_lib.api import *                   # TRex STL objects
from scapy.all import Ether, IPv6, UDP, Raw      # IPv6 stack

# --------------------
# Test parameters
# --------------------
SRC_MAC = "90:e2:ba:87:6a:84"    # L2 source MAC address
DST_MAC = "90:e2:ba:87:6a:85"    # L2 destination MAC address

SRC_IP6 = "2001:db8:10::1"       # IPv6 source (port0 / enp6s0f0)
DST_IP6 = "2001:db8:20::1"       # IPv6 destination (port1 / enp6s0f1)

TX_PORT = 0                      # TRex TX port index
RX_PORT = 1                      # TRex RX port index
PGID    = 5                      # Latency flow-stat group id

ITERATIONS = 7                                   # Number of repeated runs per (burst, pps)
BURSTS     = [1000, 10000, 100000]               # Total packets for single-burst mode
PPS_LIST   = [100, 1000, 10000]                  # Packets-per-second rates

CSV_FILE = "trex_iter_results_ipv6_udp.csv"      # Results CSV path

# ---- Packet sizing (IPv6): Ether(14) + IPv6(40) + UDP(8) + payload ----
ETHER_HDR = 14
IPV6_HDR  = 40
UDP_HDR   = 8

# Keep 18B payload to ensure room for TRex latency stamping (seq/timestamp)
# => L2 length = 14+40+8+18 = 80  -> on-wire = 84 (adds 4B FCS)
# If you want *minimal* (no payload): set LAT_PAYLOAD_SIZE = 0 (L2=62, wire=66).
LAT_PAYLOAD_SIZE = 18

PAYLOAD_SIZE = LAT_PAYLOAD_SIZE
if PAYLOAD_SIZE < 0:
    raise RuntimeError("Negative payload size! Check header sizes.")

def build_pkt():
    """Build one IPv6/UDP Ethernet frame (with payload room for latency stamping)."""
    scapy_pkt = (
        Ether(src=SRC_MAC, dst=DST_MAC) /
        IPv6(src=SRC_IP6, dst=DST_IP6) /
        UDP(dport=12, sport=1025) /
        Raw(b'X' * PAYLOAD_SIZE)
    )
    # Sanity check (optional): ensure L2 length is as expected
    expected_l2 = ETHER_HDR + IPV6_HDR + UDP_HDR + PAYLOAD_SIZE
    l2_len = len(scapy_pkt)  # Scapy len() is L2 length excluding FCS
    if l2_len != expected_l2:
        raise RuntimeError("L2 length is {} bytes, expected {}.".format(l2_len, expected_l2))
    return STLPktBuilder(pkt=scapy_pkt)

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
    Run exactly one iteration for the given (pps, burst).
    If expected duration < 1s, use continuous mode and pass duration=1.0 to c.start()
    so the latency sampler has time to populate non-zero stats.
    """
    pkt_builder = build_pkt()

    expected = (burst / float(pps)) if pps > 0 else 0.0
    short_run = expected < 1.0

    if short_run:
        mode = STLTXCont(pps=pps)     # Continuous mode (duration set at start)
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

    print("[iter {}] start -> burst={} pps={} mode={} (≈{:.2f}s)".format(
        iteration_idx, burst, pps, mode_desc, eff_duration))

    if short_run:
        c.start(ports=[TX_PORT], duration=1.0)  # auto-stop after 1s
    else:
        c.start(ports=[TX_PORT])                # single-burst stops itself

    wait_sec = max(10, int(eff_duration * 2) + 2)
    c.wait_on_traffic(ports=[TX_PORT], timeout=wait_sec)

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

