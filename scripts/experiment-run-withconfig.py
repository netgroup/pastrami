
import os
import subprocess
import json
from config import *

def run_experiment(exp_name, json_name, exp_num, duration, rate):
    print(f"Starting experiment {exp_name} at rate {rate} pkt/s for {exp_num} times")

    for i in range(1, exp_num + 1):
        print(f"Test {i}")
        cmd = [
            "python3", os.path.join(SCRIPTS_DIR, "TrexDriverCLI4_gpt.py"),
            "-s", "127.0.0.1",
            "-r", IP_REMOTE,
            "-c", "4",
            "-o", "22",
            "-u", "root",
            "--txPort", "0",
            "--rxPort", "1",
            "--rate", str(rate),
            "--duration", str(duration),
            "--pkey", PRIVATE_KEY,
            "--pcap", PCAP_PATH
        ]

        try:
            result = subprocess.check_output(cmd, text=True)
            print(result)

            pid = extract_value(result, "random_id:")
            duration_sec = extract_value(result, "duration_sec:")
            mean_cpu_load = extract_value(result, "mean_cpu_load:")
            std_dev_cpu_load = extract_value(result, "std_dev_cpu_load:")

            exp_record = [
                [rate, 4],
                {
                    "PID": pid,
                    "duration_sec": float(duration_sec),
                    "mean_cpu_load": float(mean_cpu_load),
                    "std_dev_cpu_load": float(std_dev_cpu_load)
                }
            ]

        except Exception as e:
            print(f"Failed to collect experiment result: {e}")
            exp_record = [
                [rate, 4],
                {
                    "PID": "0.0",
                    "duration_sec": 0.0,
                    "mean_cpu_load": 0.0,
                    "std_dev_cpu_load": 0.0
                }
            ]

        with open(json_name, "a") as f:
            f.write(json.dumps(exp_record) + "\n")

def extract_value(output, key):
    for line in output.splitlines():
        if key in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if key.strip(":") in p and i + 1 < len(parts):
                    return parts[i + 1].strip(",")
    return "0.0"

def run_all():
    for krl in KERNELS:
        exp_config = f"{RUNS}_exp_t_{DURATION}_{krl}_{NIC}_{NODE}"
        print(f"Experiments configuration: {exp_config}_date_{DATE}_ver_{VER}")

        print(f"Switching kernel to version {krl[1:]}")
        krl_file = subprocess.check_output(
            ["ssh", f"root@{IP_REMOTE}", f"ls /boot/vmlinuz* | grep -F {krl[1:]}"], text=True).strip()
        subprocess.run(["ssh", f"root@{IP_REMOTE}", f"{SCRIPTS_DIR}/boot-kernel.sh {krl_file}"])
        subprocess.run(["ssh", f"root@{IP_REMOTE}", "reboot"])
        print("Waiting 5 minutes for reboot...")
        subprocess.run(["sleep", "300"])
        subprocess.run(["ssh", f"root@{IP_REMOTE}", f"{SCRIPTS_DIR}/sut_init.sh"])
        subprocess.run(["ssh", f"root@{IP_REMOTE}", "uname -a"])
        print("Waiting 30 seconds before starting...")
        subprocess.run(["sleep", "30"])

        out_filename = os.path.join(
            DIR, f"{SRV}_{TESTBED}_raw_{exp_config}_nic_buf_4096_irq_pf0-4_pf1-4_date_{DATE}_ver_{VER}.txt")
        for rate in range(START, STOP + 1, STEP):
            run_experiment(NAME, out_filename, RUNS, DURATION, rate * 1000)

    print("End of experiments.")

if __name__ == "__main__":
    run_all()
