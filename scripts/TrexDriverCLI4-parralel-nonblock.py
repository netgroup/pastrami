#!/usr/bin/env python3
# encoding: utf-8

from threading import Thread
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import sys, traceback, os, paramiko, json, random, string
from TrexDriver import *

class CombinedExperiment(Thread):
    def __init__(self, server, remote, port, user, pkey_path, cpu_id, duration, txPort, rxPort, pcap, rate):
        Thread.__init__(self)
        self.server = server
        self.remote = remote
        self.port = port
        self.user = user
        self.pkey_path = pkey_path
        self.cpu_id = cpu_id
        self.duration = duration
        self.txPort = txPort
        self.rxPort = rxPort
        self.pcap = pcap
        self.rate = rate

    def gen_rnd_id(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=5))

    def run_remote_netrace(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        private_key = paramiko.RSAKey.from_private_key_file(self.pkey_path)
        ssh.connect(self.remote, port=self.port, username=self.user, pkey=private_key, timeout=30)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        command = f"cd {script_dir} && python3 cpu_load_netrace_fin.py {self.cpu_id} {self.duration} {self.rnd_id} dummy_path"
        print(f"Running remote netrace: cpu_id={self.cpu_id}, duration={self.duration}, exp_id={self.rnd_id}")
        stdin, stdout, stderr = ssh.exec_command(command)
        channel = stdout.channel

        output_remote = []
        while not channel.exit_status_ready():
            if channel.recv_ready():
                output_remote.append(channel.recv(1024).decode())
            if channel.recv_stderr_ready():
                output_remote.append(channel.recv_stderr(1024).decode())

        self.output_remote = ''.join(output_remote)
        ssh.close()

    def run_local_trex(self):
        driver = TrexDriver(self.server, self.txPort, self.rxPort, self.pcap, self.rate, self.duration)
        self.output_local = driver.run()

    def run(self):
        print("Starting Combined Experiment: Parallel Remote netrace + Local T-Rex")
        self.rnd_id = self.gen_rnd_id()

        remote_thread = Thread(target=self.run_remote_netrace)
        local_thread = Thread(target=self.run_local_trex)

        remote_thread.start()
        local_thread.start()

        remote_thread.join()
        local_thread.join()

    def response(self):
        return self.output_local, self.output_remote, self.rnd_id

def main(argv=None):
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    try:
        parser = ArgumentParser(description="", formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-l", "-s", "--local", "--server", dest="server")
        parser.add_argument("-r", "--remote", dest="remote")
        parser.add_argument("-t", "--txPort", dest="txPort", required=True)
        parser.add_argument("-x", "--rxPort", dest="rxPort", required=True)
        parser.add_argument("-p", "--pcap", dest="pcap", required=True)
        parser.add_argument("-e", "--rate", dest="rate", required=True)
        parser.add_argument("-d", "--duration", dest="duration", required=True)
        parser.add_argument("-c", "--cpu_id", dest="cpu_id", required=True)
        parser.add_argument("-o", "--ssh_port", dest="ssh_port", required=True)
        parser.add_argument("-u", "--user", dest="user", required=True)
        parser.add_argument("-k", "--pkey", dest="pkey_path", required=True)

        args = parser.parse_args()

        combined_thread = CombinedExperiment(
            server=args.server or '127.0.0.1',
            remote=args.remote,
            port=int(args.ssh_port),
            user=args.user,
            pkey_path=args.pkey_path,
            cpu_id=int(args.cpu_id),
            duration=int(args.duration),
            txPort=int(args.txPort),
            rxPort=int(args.rxPort),
            pcap=args.pcap,
            rate=args.rate
        )

        combined_thread.start()
        combined_thread.join()

        output_local, output_remote, rnd_id = combined_thread.response()

        print("cpu_load_output:")

        last_brace_open = output_remote.rfind('{')
        last_brace_close = output_remote.rfind('}')
        cpu_result = None

        if last_brace_open != -1 and last_brace_close != -1 and last_brace_close > last_brace_open:
            try:
                maybe_json = output_remote[last_brace_open:last_brace_close+1]
                parsed = json.loads(maybe_json)
                if "mean_cpu_load" in parsed:
                    cpu_result = parsed
            except json.JSONDecodeError as e:
                print("JSON decode error:", e)

        if not cpu_result:
            print("Raw SSH output for debugging:")
            print(output_remote)
            raise ValueError("Failed to extract JSON CPU result from remote output.")

        cpu_result["random_id"] = rnd_id

        print(f"TX: {output_local.getTxTotalPackets()}")
        print(f"RX: {output_local.getRxTotalPackets()}")
        print(f"mean_cpu_load: {cpu_result['mean_cpu_load']}")
        print(f"std_dev_cpu_load: {cpu_result['std_dev_cpu_load']}")
        print(f"random_id: {cpu_result['random_id']}")
        print(f"duration_sec: {cpu_result['duration_sec']}")
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception:
        print('-' * 60)
        print("Exception in user code:")
        traceback.print_exc(file=sys.stdout)
        print('-' * 60)
        return 2

if __name__ == "__main__":
    sys.exit(main())
