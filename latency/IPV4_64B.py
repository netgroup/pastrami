#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, csv, time, os
sys.path.insert(0, "/opt/v3.06/automation/trex_control_plane/interactive")
sys.path.insert(0, "/opt/v3.06/external_libs/scapy-2.4.3")

from trex_stl_lib.api import *
from scapy.all import Ether, IP, UDP, Raw

# --------------------
# Defaults (will be overwritten by CSV)
# --------------------
SRC_MAC = "00:00:00:00:11:11"
DST_MAC = "00:00:00:00:22:22"

TX_PORT = 0
RX_PORT = 1
PGID    = 5

ITERATIONS = 7
BURSTS     = [1000, 10000, 100000]
PPS_LIST   = [100, 1000, 10000]

CSV_FILE = "trex_iter_results_64B_ipv4_fix.csv"   # results CSV
MACS_CSV = "macs.csv"                              # input CSV with MACs

# ---- Packet sizing: exact 64B on wire (60B L2 + 4B FCS) ----
ETHER_HDR = 14
IP_HDR    = 20
UDP_HDR   = 8
PAYLOAD_SIZE = 60 - (ETHER_HDR + IP_HDR + UDP_HDR)  # 18
if PAYLOAD_SIZE < 0:
    raise RuntimeError("Negative payload size! Check header sizes.")
PAYLOAD = b'X' * PAYLOAD_SIZE

def read_macs_from_csv(path, tx_port=0, rx_port=1):
    """
    macs.csv format:
      PCI_Address,MAC_Address,Driver
      0000:06:00.0,AA:BB:...,net_ixgbe
      0000:06:00.1,CC:DD:...,net_ixgbe

    انتخاب:
      - اگر سطرها شامل .0 و .1 باشند -> .0 برای TX، .1 برای RX
      - وگرنه: دو سطر اول به ترتیب TX, RX
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"MAC CSV not found: {path}")

    with open(path, newline="") as f:
        rdr = csv.DictReader(f)
        rows = [r for r in rdr]

    if not rows:
        raise ValueError("MAC CSV is empty.")

    # سعی بر اساس PCI
    mac_tx = mac_rx = None
    for r in rows:
        pci = (r.get("PCI_Address") or "").strip()
        mac = (r.get("MAC_Address") or "").strip()
        if pci.endswith(".0") and not mac_tx:
            mac_tx = mac
        if pci.endswith(".1") and not mac_rx:
            mac_rx = mac

    # اگر با PCI پیدا نشد، از ترتیب استفاده کن
    if not mac_tx or not mac_rx:
        if len(rows) < 2:
            raise ValueError("Need at least two rows in MAC CSV.")
        mac_tx = mac_tx or (rows[0].get("MAC_Address") or "").strip()
        mac_rx = mac_rx or (rows[1].get("MAC_Address") or "").strip()

    # sanity
    if not mac_tx or not mac_rx:
        raise ValueError(f"Could not parse MACs from CSV: tx='{mac_tx}' rx='{mac_rx}'")

    return mac_tx, mac_rx

def build_pkt():
    scapy_pkt = (
        Ether(src=SRC_MAC, dst=DST_MAC) /
        IP(src="10.10.2.1", dst="10.10.1.1") /
        UDP(dport=12, sport=1025) /
        Raw(PAYLOAD)
    )
    if len(scapy_pkt) != 60:
        raise RuntimeError(f"L2 length is {len(scapy_pkt)} bytes, expected 60.")
    return STLPktBuilder(pkt=scapy_pkt)

def ensure_csv_header(path):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow([
                "timestamp","iteration","pps","burst",
                "tx_pkts","rx_pkts","tx_bps_l1","rx_bps_l1",
                "avg_latency_us","min_latency_us","max_latency_us","jitter_us",
                "drops","ooo","dup","seq_too_high","seq_too_low"
            ])

def one_iteration(c, pps, burst, iteration_idx):
    pkt_builder = build_pkt()

    expected = (burst / float(pps)) if pps > 0 else 0.0
    short_run = expected < 1.0

    if short_run:
        mode = STLTXCont(pps=pps); mode_desc="CONT 1s"; eff_duration=1.0
    else:
        mode = STLTXSingleBurst(total_pkts=burst, pps=pps); mode_desc="SINGLE"; eff_duration=expected

    s = STLStream(name="lat", packet=pkt_builder,
                  flow_stats=STLFlowLatencyStats(pg_id=PGID),
                  mode=mode)

    c.reset(ports=[TX_PORT, RX_PORT])
    c.add_streams(s, ports=[TX_PORT])
    c.clear_stats()

    print(f"[iter {iteration_idx}] start -> burst={burst} pps={pps} mode={mode_desc} (≈{eff_duration:.2f}s)")

    if short_run: c.start(ports=[TX_PORT], duration=1.0)
    else:         c.start(ports=[TX_PORT])

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
        "iteration": iteration_idx, "pps": pps, "burst": burst,
        "tx_pkts": tx_pkts, "rx_pkts": rx_pkts,
        "tx_bps_l1": tx_bps_l1, "rx_bps_l1": rx_bps_l1,
        "avg_latency_us": avg_us, "min_latency_us": min_us, "max_latency_us": max_us, "jitter_us": jitter_us,
        "drops": errc.get('dropped', 0), "ooo": errc.get('out_of_order', 0), "dup": errc.get('dup', 0),
        "seq_too_high": errc.get('seq_too_high', 0), "seq_too_low": errc.get('seq_too_low', 0)
    }

    print(f"[iter {iteration_idx}] TX:{tx_pkts} RX:{rx_pkts} AVG:{avg_us:.1f}us MIN:{min_us:.1f}us MAX:{max_us:.1f}us JIT:{jitter_us:.1f}us")
    return row

def main():
    global SRC_MAC, DST_MAC

    # 1) MACها را از macs.csv کنار اسکریپت بخوان
    here = os.getcwd()
    macs_csv_path = os.path.join(here, MACS_CSV)
    try:
        mac_tx, mac_rx = read_macs_from_csv(macs_csv_path, TX_PORT, RX_PORT)
        SRC_MAC, DST_MAC = mac_tx, mac_rx
        print(f"Using MACs from '{macs_csv_path}': SRC(TX)={SRC_MAC}  DST(RX)={DST_MAC}")
    except Exception as e:
        print(f"[WARN] Could not read '{macs_csv_path}' -> using default MACs. Reason: {e}")

    # 2) ادامه‌ی روال قبلی
    ensure_csv_header(CSV_FILE)
    c = STLClient()
    c.connect()
    try:
        with open(CSV_FILE, "a", newline="") as f:
            w = csv.writer(f)
            for burst in BURSTS:
                for pps in PPS_LIST:
                    print("="*60)
                    print(f"Experiment -> BURST={burst}  PPS={pps}")
                    print("="*60)
                    for it in range(1, ITERATIONS+1):
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
