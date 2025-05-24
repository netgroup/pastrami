#!/usr/bin/env python3
"""
Final Experiment Runner - Exact TRex Command Matching Original Script
"""

import os
import sys
import json
import time
import subprocess
import paramiko
import numpy as np
from datetime import datetime

###############################################
# Configuration (Matches Your Original)
###############################################

BASE_DIR = os.getenv('PASTRAMI_BASE_DIR', os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(BASE_DIR, "netrace_data", "test-0")
NETRACE = os.path.join(SCRIPTS_DIR, "netrace")
# Experiment parameters
NAME = "clab_cpu"
START = 250
STOP = 260
STEP = 10
RUNS = 1
DURATION = 30

# System configuration
NIC = "intel"
NODE = "bare-metal"
SRV = "clab"
TESTBED = "tb0"
DATE = datetime.now().strftime("%Y-%m-%dT%H:%M")
VER = "01"
IP_REMOTE = "128.105.145.228"
KERNEL = ["k5.15"]

os.makedirs(DIR, exist_ok=True)

###############################################
# TRex Driver (Exact Original Implementation)
###############################################

def run_trex_command(rate, duration, exp_id):
    """Execute the exact TRex command from your original script"""
    try:
        # Exact command structure from your original script
        cmd = [
            "python3", os.path.join(SCRIPTS_DIR, "TrexDriverCLI-shark.py"),
            "-s", "127.0.0.1",
            "-r", IP_REMOTE,
            "-c", "4",
            "-o", "22",
            "-u", "root",
            "--txPort", "0",
            "--rxPort", "1",
            "--rate", str(rate),
            "--duration", str(duration),
            "--pkey", "/root/.ssh/id_rsa",
            "--pcap", "/proj/superfluidity-PG0/srperf2/pcap/trex-pcap-files/plain-ipv6-64.pcap"
        ]
        
        # Execute with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=duration + 30
        )
        
        output = result.stdout.strip()
        print(f"TRex Output:\n{output}")
        
        # Parse output exactly as in original script
        metrics = {
            'tx_packets': int(output.split('tx_packets:')[1].split()[0]),
            'rx_packets': int(output.split('rx_packets:')[1].split()[0]),
            'mean_cpu_load': float(output.split('mean_cpu_load:')[1].split()[0]),
            'std_dev_cpu_load': float(output.split('std_dev_cpu_load:')[1].split()[0]),
            'random_id': output.split('random_id:')[1].split()[0].strip('"')
        }
        
        return metrics
        
    except subprocess.TimeoutExpired:
        print("ERROR: TRex command timed out")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: TRex command failed (exit code {e.returncode})")
        print(f"Command: {e.cmd}")
        print(f"Error output:\n{e.stderr}")
    except Exception as e:
        print(f"ERROR: {str(e)}")
    
    return None

###############################################
# Netrace Monitoring (Improved Version)
###############################################

class NetraceMonitor:
    def __init__(self):
        self.cpu_loads = []
    
    def start(self, duration, exp_id):
        """Start netrace monitoring"""
        try:
            self.output_file = f"cpu_load_exp_id_{exp_id}.txt"
            self.process = subprocess.Popen(
                NETRACE,
                stdout=open(self.output_file, 'w'),
                stderr=subprocess.PIPE
            )
            time.sleep(duration)
            self.stop()
            return True
        except Exception as e:
            print(f"Netrace Start Error: {str(e)}")
            return False
    
    def stop(self):
        """Stop netrace monitoring"""
        if hasattr(self, 'process'):
            self.process.send_signal(signal.SIGINT) #erorr is due to this command signal
            self.process.wait()
    
    def parse_results(self):
        """Parse CPU usage from netrace output"""
        try:
            with open(self.output_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        if data.get("name") == "EVENT_NET_RX_SOFTIRQ":
                            for usage in data.get("cpu_usage", []):
                                for cpu, value in usage.items():
                                    self.cpu_loads.append(float(value))
                    except json.JSONDecodeError:
                        continue
            
            # Calculate stats (skip first 2 and last 1 seconds)
            if len(self.cpu_loads) > 3:
                valid_data = self.cpu_loads[2:-1]
                return {
                    'mean': float(np.mean(valid_data)),
                    'std_dev': float(np.std(valid_data)),
                    'raw': valid_data
                }
            return None
            
        except Exception as e:
            print(f"CPU Parse Error: {str(e)}")
            return None

###############################################
# Experiment Runner (Main Logic)
###############################################

def experiment(exp_name, json_name, exp_num, duration, rate):
    """Single experiment run matching original structure"""
    print(f"Starting experiment {exp_name} at rate {rate} pkt/s")
    
    results = []
    
    for i in range(1, exp_num + 1):
        print(f"Test {i}")
        
        # Start netrace
        monitor = NetraceMonitor()
        if not monitor.start(duration, f"{exp_name}_{rate}_{i}"):
            continue
        
        # Run TRex command (exact original)
        trex_metrics = run_trex_command(rate, duration, f"{exp_name}_{rate}_{i}")
        if not trex_metrics:
            continue
        
        # Get CPU stats
        cpu_stats = monitor.parse_results()
        
        if cpu_stats:
            result = {
                'rate': rate,
                'tx_packets': trex_metrics['tx_packets'],
                'rx_packets': trex_metrics['rx_packets'],
                'cpu_load': cpu_stats,
                'random_id': trex_metrics['random_id'],
                'test_num': i
            }
            results.append(result)
            print(f"Result {i}:\n{json.dumps(result, indent=2)}")
    
    # Save results
    if results:
        with open(json_name, 'a') as f:
            json.dump(results, f, indent=2)
            f.write("\n")
    
    print("Experiment completed\n")

def main():
    """Main execution matching your original script"""
    print(f"Starting experiments at {DATE}")
    
    for KRL in KERNEL:
        EXPCONFIG = f"{RUNS}_exp_t_{DURATION}_{KRL}_{NIC}_{NODE}"
        print(f"\nExperiments configuration: {EXPCONFIG}")
        
        # Setup SUT (simplified from original)
        print("Configuring SUT node")
        try:
            # Kernel switching (from original)
            krl_file = subprocess.run(
                ["ssh", f"root@{IP_REMOTE}", f"ls /boot/vmlinuz* | grep -F {KRL[1:]}"],
                capture_output=True, text=True, check=True
            ).stdout.strip()
            
            subprocess.run([
                "ssh", f"root@{IP_REMOTE}",
                os.path.join(SCRIPTS_DIR, "boot-kernel.sh"), krl_file
            ], check=True)
            time.sleep(5)
            
            # SUT initialization (from original)
            subprocess.run([
                "ssh", f"root@{IP_REMOTE}",
                os.path.join(SCRIPTS_DIR, "sut_init.sh")
            ], check=True)
            time.sleep(5)
            
            print("Kernel version:")
            subprocess.run(["ssh", f"root@{IP_REMOTE}", "uname -a"], check=True)
            
        except subprocess.CalledProcessError as e:
            print(f"SUT Setup Error: {e.stderr}")
            continue
        
        # Run experiments
        print(f"\nStarting experiment: {EXPCONFIG}")
        outfile = os.path.join(DIR, 
            f"{SRV}_{TESTBED}_raw_{EXPCONFIG}_nic_buf_4096_irq_pf0-4_pf1-4_date_{DATE}_ver_{VER}.json")
        
        rates = [r * 1000 for r in range(START, STOP + 1, STEP)]
        print(f"Testing rates: {rates}")
        
        for rate in rates:
            experiment(NAME, outfile, RUNS, DURATION, rate)
    
    print("\nAll experiments completed")

if __name__ == "__main__":
    # Verify requirements
    try:
        import paramiko
        import numpy as np
    except ImportError as e:
        print(f"Error: {str(e)}")
        print("Required packages: pip install paramiko numpy")
        sys.exit(1)
    
    main()
