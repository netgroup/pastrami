
import os
import datetime

# Experiment Configuration
NAME = "clab_cpu"
START = 250
STOP = 260
STEP = 10
RUNS = 1
DURATION = 30
NIC = "intel"
NODE = "bare-metal"
SRV = "clab"
TESTBED = "tb0"
DATE = datetime.datetime.now().isoformat(timespec='minutes')
VER = "01"
IP_REMOTE = "128.105.145.228"
KERNELS = ["k5.15"]
#KERNEL= ["k5.10" "k5.12" "k5.15" "k5.19" "k6.2" "k6.5" "k6.8" "k6.10" "k6.12" "k6.13" "k6.14"]
# Paths
BASE_DIR = os.getenv("PASTRAMI_BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = BASE_DIR
DIR = os.path.join(BASE_DIR, "netrace_data", "test-0")
os.makedirs(DIR, exist_ok=True)

# Other
PCAP_PATH = "/proj/superfluidity-PG0/srperf2/pcap/trex-pcap-files/plain-ipv6-64.pcap"
PRIVATE_KEY = "/root/.ssh/id_rsa"
