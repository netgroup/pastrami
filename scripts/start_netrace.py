import json
import subprocess
import time
import signal
import os

# Load config from JSON
with open('rm_config.json') as f:
    config = json.load(f)

duration = config['duration']
exp_id = config['exp_id']

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define the output directory as 'rm' inside the script directory
output_dir = os.path.join(script_dir, 'rm')
os.makedirs(output_dir, exist_ok=True)

# Define the full output filename path
output_filename = os.path.join(output_dir, f"cpu_load_exp_id_{exp_id}.txt")

# Define netrace binary path dynamically (inside the same directory as this script)
netrace_path = os.path.join(script_dir, "netrace")

if not os.path.isfile(netrace_path):
    raise FileNotFoundError(f"netrace binary not found at: {netrace_path}")

# Make sure it has execute permission
os.chmod(netrace_path, 0o755)

# Start the netrace process and capture its output
with open(output_filename, 'w') as outfile:
    print(f"Starting {netrace_path} ...")
    process = subprocess.Popen(
        [netrace_path],
        stdout=outfile,
        stderr=subprocess.STDOUT
    )

    print(f"%%% PID: {process.pid} %%%")

    # Run for the specified duration
    time.sleep(duration)

    # Send SIGINT to stop netrace gracefully
    print("Sending SIGINT to netrace...")
    process.send_signal(signal.SIGINT)
    process.wait()

    print("netrace terminated.")
    print(f"Output saved to: {output_filename}")
