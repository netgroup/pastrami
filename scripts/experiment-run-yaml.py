import os
import subprocess
import json
import yaml
import datetime
import time
import paramiko

# Read config from YAML
with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)

# Assign variables
NAME = config['NAME']
START = config['START']
STOP = config['STOP']
STEP = config['STEP']
RUNS = config['RUNS']
DURATION = config['DURATION']
NIC = config['NIC']
NODE = config['NODE']
SRV = config['SRV']
TESTBED = config['TESTBED']
VER = config['VER']
IP_REMOTE = config['IP_REMOTE']
KERNELS = config['KERNELS']
PCAP_PATH = config['PCAP_PATH']
PRIVATE_KEY = config['PRIVATE_KEY']
CPU_NUM = config['CPU_NUM']
# Dynamic values
DATE = datetime.datetime.now().isoformat(timespec='minutes')
BASE_DIR = os.getenv("PASTRAMI_BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = BASE_DIR
DIR = os.path.join(BASE_DIR, "netrace_data", "test-0")
os.makedirs(DIR, exist_ok=True)
pcap_path = os.path.join(SCRIPTS_DIR, PCAP_PATH)

# Initialize Paramiko SSH client
def create_ssh_client():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(IP_REMOTE, username="root", key_filename=PRIVATE_KEY)
    return client

ssh_client = create_ssh_client()

def run_remote_cmd(client, cmd):
    """Execute a command on the remote server and return stdout."""
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if err:
        print(f"[REMOTE ERROR]: {err}")
    return out.strip()


def run_experiment(exp_name, json_name, exp_num, duration, rate):
    print(f"Starting experiment {exp_name} at rate {rate} pkt/s for {exp_num} times")

    for i in range(1, exp_num + 1):
        print(f"Test {i}")
        cmd = [
            "python3", os.path.join(SCRIPTS_DIR, "TrexDriverCLI4-parralel-nonblock.py"),
            "-s", "127.0.0.1",
            "-r", IP_REMOTE,
            "-c", CPU_NUM,
            "-o", "22",
            "-u", "root",
            "--txPort", "0",
            "--rxPort", "1",
            "--rate", str(rate),
            "--duration", str(duration),
            "--pkey", PRIVATE_KEY,
            "--pcap", pcap_path
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


def wait_for_ssh(timeout=600, interval=10):
    """Wait for server to come back online after reboot."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            client = create_ssh_client()
            print("Reconnected to server.")
            return client
        except Exception:
            print("Waiting for server to come back online...")
            time.sleep(interval)
    raise RuntimeError("Failed to reconnect to server after reboot")


def run_all():
    global ssh_client
    for krl in KERNELS:
        exp_config = f"{RUNS}_exp_t_{DURATION}_{krl}_{NIC}_{NODE}"
        print(f"Experiments configuration: {exp_config}_date_{DATE}_ver_{VER}")

        print(f"Switching kernel to version {krl[1:]}")
        krl_file = run_remote_cmd(ssh_client, f"ls /boot/vmlinuz* | grep -F {krl[1:]}")
        run_remote_cmd(ssh_client, f"{SCRIPTS_DIR}/boot-kernel.sh {krl_file}")

        print("Rebooting server...")
        run_remote_cmd(ssh_client, "reboot")
        ssh_client.close()

        print("Waiting 5 minutes for server to reboot...")
        time.sleep(300)  # waite 5 minuts to resume
        print("Reconnecting to server...")
        ssh_client = create_ssh_client()  # reconnect to client after reboot

        print("Initializing SUT...")
        run_remote_cmd(ssh_client, f"{SCRIPTS_DIR}/sut_init.sh")
        print(run_remote_cmd(ssh_client, "uname -a"))

        print("Waiting 30 seconds before starting experiments...")
        time.sleep(30)

        out_filename = os.path.join(
            DIR, f"{SRV}_{TESTBED}_raw_{exp_config}_nic_buf_4096_irq_pf0-4_pf1-4_date_{DATE}_ver_{VER}.txt"
        )

        for rate in range(START, STOP + 1, STEP):
            run_experiment(NAME, out_filename, RUNS, DURATION, rate * 1000)

    ssh_client.close()
    print("End of experiments.")



if __name__ == "__main__":
    run_all()
