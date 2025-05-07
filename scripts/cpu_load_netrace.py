#!/usr/bin/env python3
# encoding: utf-8

import time, json, sys, os
import subprocess
import numpy as np


def parse_cpu_usage(file_path, cpu_id):
    cpu_load = []

    with open(file_path, 'r') as file:
        for line in file:
            try:
                # Parse the JSON line
                data = json.loads(line.strip())

                # Iterate through events to find the desired event
                for event in data.get("events", []):
                    if event["name"] == "EVENT_NET_RX_SOFTIRQ":
                        cpu_usage = event.get("cpu_usage", [])
                        if cpu_usage:
                            for usage in cpu_usage:
                                for cpu, value in usage.items():
                                    if int(cpu) == cpu_id:
                                        cpu_load.append(value)
                        else:
                            print("No CPU usage data for EVENT_NET_RX_SOFTIRQ.")
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
            except Exception as e:
                print(f"An error occurred: {e}")
    return cpu_load


def main():
    cpu_loads = []

    # Get the CPU number from commandline
    cpu_id = int(sys.argv[1])

    # Get the experiment duration from commandline
    duration = int(sys.argv[2])

    # Get the experiment code from commandline
    exp_id = sys.argv[3]

    # Get the nettrace path from commandline
    file_path = sys.argv[4]

    # Call the script that execute the eBPF netrace command: ex. ./netrace | tee cpu_load_exp_id_AAAAA.txt
    subprocess.run(['/proj/superfluidity-PG0/pastrami/scripts/start_netrace.sh', str(duration), exp_id], check=True, capture_output=True)

    # Wait 2 seconds before process data
    time.sleep(2)

    # Process the cpu load data
    cpu_loads = parse_cpu_usage(file_path, cpu_id)

    min_range = int(2)
    max_range = int(duration - 1)

    # Extract values from 3rd second to the duration time
    selected_cpu_loads = cpu_loads[min_range:max_range]

    # Calculate mean and standard deviation
    mean_cpu_load = np.mean(selected_cpu_loads)
    std_dev_cpu_load = np.std(selected_cpu_loads)

    print(f"[{mean_cpu_load:.2f}, {std_dev_cpu_load:.2f}]")

if __name__ == "__main__":
    main()
