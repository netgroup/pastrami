To run the experiment for CPU performance, the first step is to select the configuration that you want inside the config.yml file inside the TG node.
open the config.yml file and fallow the steps.
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
  port1: enn1  #please insert the first port name here
  port2: enp0s6f1  #please insert the second port name here
