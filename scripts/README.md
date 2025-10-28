🧠 CPU Performance Experiment (TG Node)

To run the CPU performance experiment, follow the steps below:

1️⃣ Edit the Configuration File

On the TG node, open the configuration file located at:
```bash
/scripts/config.yml
```
This file defines all parameters used for the experiment.
Open it with your preferred editor (for example, nano):
```bash
sudo nano /users/<username>/pastrami/scripts/config.yml
```
Then, adjust the parameters as needed.
Below is an example configuration:
```bash
NAME: "clab_cpu"
START: 250
STOP: 260
STEP: 10
RUNS: 1
DURATION: 30
NIC: "intel"
NODE: "bare-metal"
SRV: "clab"
TESTBED: "tb0"
VER: "01"
IP_REMOTE: "128.105.145.252"
CPU_NUM: 4

KERNELS:
  - "k5.15"
#KERNELS_DISABLED:
#  - "k5.10"
#  - "k5.12"
#  - "k5.15"
#  - "k5.19"
#  - "k6.2"
#  - "k6.5"
#  - "k6.8"
#  - "k6.10"
#  - "k6.12"
#  - "k6.13"
#  - "k6.14"

PCAP_PATH: "pcap/plain-ipv6-64.pcap"
PRIVATE_KEY: "sshkeys/tg_to_sut"

interfaces:
  port1: "enp1s0f0"   # please insert the first interface name here
  port2: "enp1s0f1"   # please insert the second interface name here

```
2️⃣ Notes

Make sure that IP_REMOTE matches the SUT node’s IPv4 address.

Update PRIVATE_KEY if you use a different SSH key path.

The interfaces section should contain the exact NIC names of your TG node (you can verify them with ip link show).

Only one kernel can be active at a time inside KERNELS.

All other kernel versions should remain commented under KERNELS_DISABLED.
