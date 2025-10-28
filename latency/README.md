Latency Experiment

> ⚠️ **Note:**  
> If you haven’t run the **CPU experiment** before, please go to the `/scripts` directory and complete **steps 1 to 3** in its `README.md` file first.  
> Once those steps are done, you can proceed with the steps below for the latency experiment.

To run the latency performance experiment, please follow the steps below:

1️⃣ Open the latency configuration file with your preferred text editor (e.g., nano):
```bash
sudo nano latency_config.yaml
```
2️⃣ Inside the file, locate the selected_test section and specify which test you want to run.
You can choose one from the list of available tests, as shown in the example below:
```bash 
tests:
  IPV4_64B: "IPV4_64B.py"
  IPV4_1500B: "IPV4_1500B.py"
  IPV6_64B: "IPV6_64B.py"
  MAConly_64B: "MAConly_64B.py"
  MAConly_1500B: "MAConly_1500B.py"

selected_test: "MAConly_64B"
```
📘 Note:
The selected_test key determines which Python script will be executed when running the latency experiment.

3️⃣ Run the mac_writer_csv.sh script using the command below.
This script reads the real MAC addresses from the network interfaces and writes them into the macs.csv file
```bash
sudo ./mac_writer_scv.sh
```
You can verify that the script ran successfully by using the command below:
```bash 
cat macs.csv
```
You should see the PCI address, MAC address, and driver listed — for example:
```bash 
PCI_Address,MAC_Address,Driver
0000:06:00.0,90:E2:BA:38:37:C8,net_ixgbe
0000:06:00.1,90:E2:BA:38:37:C9,net_ixgbe
```
4️⃣  If you have not run the **CPU performance experiment** before, please execute the following script to automatically install all required tools and configurations:
```bash
sudo ./instalation.sh
```
5️⃣ At the end, to run the **latency experiment**, please execute the following command:
```bash
sudo ./run_experiment.sh
```
After running the experiment script, you will see the results of each iteration printed on the screen.
If all the steps were completed successfully, the TX and RX packet counters should both be non-zero.

Once the test is finished, a CSV file containing the experiment results will be generated automatically — for example:
```bash
trex_iter_results_64B_ipv4_fix.csv
```

