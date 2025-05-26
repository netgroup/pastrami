#!/usr/bin/env python3
# encoding: utf-8

from threading import Thread
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import sys, traceback, os, paramiko, json, random, string
from TrexDriver import *

class CPULoad(Thread):
    def __init__(self, remote, port, user, pkey_path, cpu_id, duration):
        Thread.__init__(self)
        self.remote = remote
        self.port = port
        self.user = user
        self.pkey_path = pkey_path
        self.cpu_id = cpu_id
        self.duration = duration

    def gen_rnd_id(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=5))

    def run(self):
        print("Starting Measuring HW and SW irq on CPU", self.cpu_id)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        private_key = paramiko.RSAKey.from_private_key_file(self.pkey_path)

        self.rnd_id = self.gen_rnd_id()

        try:
            ssh.connect(self.remote, port=self.port, username=self.user, pkey=private_key)
            script_dir = "/users/Rmoradi/pastrami/scripts"
            command = f"cd {script_dir} && python3 cpu_load_netrace_gpt.py {self.cpu_id} {self.duration} {self.rnd_id} dummy_path"
            stdin, stdout, stderr = ssh.exec_command(command)
            self.output = stdout.read().decode() + stderr.read().decode()
            print("SSH output: ", self.output)
        finally:
            ssh.close()

        print("Stopping Measuring HW and SW irq on CPU", self.cpu_id)

    def response(self):
        return self.output, self.rnd_id


class TrexRun(Thread):
    def __init__(self, server, txPort, rxPort, pcap, rate, duration):
        Thread.__init__(self)
        self.server = server
        self.txPort = txPort
        self.rxPort = rxPort
        self.pcap = pcap
        self.rate = rate
        self.duration = duration
        self.output = ""

    def run(self):
        print("Starting T-Rex on:", self.server)
        driver = TrexDriver(self.server, self.txPort, self.rxPort, self.pcap, self.rate, self.duration)
        self.output = driver.run()
        print("End thread:", self.server)

    def response(self):
        return self.output


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

        server = args.server or '127.0.0.1'
        remote = args.remote
        txPort = int(args.txPort)
        rxPort = int(args.rxPort)
        pcap = args.pcap
        rate = args.rate
        duration = int(args.duration)
        cpu_id = int(args.cpu_id)
        port = int(args.ssh_port)
        user = args.user
        pkey_path = args.pkey_path

        thread2 = CPULoad(remote, port, user, pkey_path, cpu_id, duration)
        thread2.start()

        thread1 = TrexRun(server, txPort, rxPort, pcap, rate, duration)
        thread1.start()

        thread2.join()
        output_local = thread1.response()
        output_remote, rnd_id = thread2.response()

        print("cpu_load_output:")

        # Find the last complete JSON block and parse it
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
