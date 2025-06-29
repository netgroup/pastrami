#!/usr/bin/env python3
# encoding: utf-8

import time
import json
import sys
import os
import subprocess
import numpy as np

def parse_cpu_usage(file_path, cpu_id):
    cpu_load = []

    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()

            # Skip empty lines or libbpf logs
            if not line or not line.startswith("{"):
                continue

            try:
                # Parse the JSON line
                data = json.loads(line)

                for event in data.get("events", []):
                    if event["name"] == "EVENT_NET_RX_SOFTIRQ":
                        cpu_usage = event.get("cpu_usage", [])
                        if cpu_usage:
                            for usage in cpu_usage:
                                for cpu, value in usage.items():
                                    if int(cpu) == cpu_id:
                                        cpu_load.append(value)
            except json.JSONDecodeError:
                continue  # skip bad lines silently
            except Exception as e:
                print(f"Unexpected error: {e}")
                continue

    return cpu_load



def main():
    # Check command line arguments
    if len(sys.argv) < 5:
        print("Usage: cpu_load_netrace.py <cpu_id> <duration> <exp_id> <output_path_placeholder>")
        sys.exit(1)

    cpu_id = int(sys.argv[1])
    duration = int(sys.argv[2])
    exp_id = sys.argv[3]
    output_path = sys.argv[4]  # Not used, placeholder for compatibility

    # Prepare config dict for start_netrace.py
    config = {
        "duration": duration,
        "exp_id": exp_id
    }

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'rm_config.json')

    # Write config JSON
    with open(config_path, 'w') as f:
        json.dump(config, f)

    # Run start_netrace.py with config
    start_netrace_path = os.path.join(script_dir, 'start_netrace.py')
    subprocess.run([sys.executable, start_netrace_path, config_path], check=True)

    # Wait a little before processing output
    time.sleep(2)

    output_file = os.path.join(script_dir, 'rm', f"cpu_load_exp_id_{exp_id}.txt")

    cpu_loads = parse_cpu_usage(output_file, cpu_id)

    # Analyze CPU loads between 3rd second and last but one second
    min_range = 2
    max_range = duration - 1
    selected_cpu_loads = cpu_loads[min_range:max_range]

    # Calculate mean and std deviation safely
    if selected_cpu_loads:
        mean_cpu_load = np.mean(selected_cpu_loads)
        std_dev_cpu_load = np.std(selected_cpu_loads)
    else:
        mean_cpu_load = 0.0
        std_dev_cpu_load = 0.0

    # Prepare result dictionary
    results = {
        "cpu_id": cpu_id,
        "experiment_id": exp_id,
        "duration_sec": duration,
        "mean_cpu_load": round(mean_cpu_load, 2),
        "std_dev_cpu_load": round(std_dev_cpu_load, 2),
        "samples_analyzed": len(selected_cpu_loads)
    }

    # Print results as pretty JSON
    print(json.dumps(results, indent=4))


if __name__ == "__main__":
    main()
