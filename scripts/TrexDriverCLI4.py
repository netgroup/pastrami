#!/usr/bin/env python3
# encoding: utf-8

from threading import Thread
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import sys, traceback, re, numpy, paramiko
import random, string

from TrexDriver import *

class CPULoad (Thread):
    def __init__(self, remote, port, user, pkey_path, cpu_id, duration):
        Thread.__init__(self)
        self.remote = remote
        self.port = port
        self.user = user
        self.pkey_path = pkey_path
        self.cpu_id = cpu_id
        self.duration=duration

    def gen_rnd_id(self):
        # Define the characters to choose from: letters and digits
        characters = string.ascii_letters + string.digits

        # Generate a random string of 5 characters
        random_string = ''.join(random.choice(characters) for _ in range(5))

        return random_string

    def run(self):
        print ("Starting Measuring HW and SW irq on CPU", self.cpu_id)

        # Create an SSH client
        ssh = paramiko.SSHClient()
        # Automatically add the server's host key (you might want to handle this differently in production)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Load your private key
        private_key = paramiko.RSAKey.from_private_key_file(self.pkey_path)

        self.rnd_id = self.gen_rnd_id()

        # Connect to the server using the private key
        try:
            ssh.connect(self.remote, username=self.user, pkey=private_key)
            # Execute a command (optional)
            stdin, stdout, stderr = ssh.exec_command(f"python3 /proj/superfluidity-PG0/pastrami/scripts/cpu_load_netrace.py {self.cpu_id} {self.duration} {self.rnd_id} cpu_load_exp_id_{self.rnd_id}.txt")
            #stdin, stdout, stderr = ssh.exec_command(f"ls")
            self.output = stdout.read().decode()
            print ("SSH output: ", self.output)

        finally:
            # Close the connection
            ssh.close()
        print("Stopping Measuring HW and SW irq on CPU %s\n" % self.cpu_id)

    def response(self):
        return self.output, self.rnd_id



class TrexRun (Thread):
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
        print ("Starting T-Rex on:", self.server)
        driver = TrexDriver(self.server, self.txPort, self.rxPort, self.pcap, self.rate, self.duration)
        self.output = driver.run()
        print("End thread: %s \n" % self.server)

    def response(self):
        return self.output


def main(argv=None):  # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    try:
        # Setup argument parser
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

        # Process arguments
        args = parser.parse_args()

        server = args.server
        if server is None:
            server = '127.0.0.1'

        server = str(server)
        remote = str(args.remote)
        txPort = int(args.txPort)
        rxPort = int(args.rxPort)
        pcap = str(args.pcap)
        rate = str(args.rate)
        duration = int(args.duration)
        cpu_id = int(args.cpu_id)
        port = int(args.ssh_port)
        user = str(args.user)
        pkey_path = str(args.pkey_path)

        thread2 = CPULoad(remote, port, user, pkey_path, cpu_id, duration)
        thread2.start()

        thread1 = TrexRun(server, txPort, rxPort, pcap, rate, duration)
        thread1.start()

        # Print out results
        thread2.join()
        output_local = thread1.response()
        output_remote, rnd_id = thread2.response()
        print ("cpu_load_output: ", output_remote)
        cpu_load_list = json.loads(output_remote)
        cpu_load_list.append(rnd_id)

        print ("TX:", output_local.getTxTotalPackets())
        print ("RX:", output_local.getRxTotalPackets())
        print ("mean_cpu_load:", cpu_load_list[0])
        print ("std_dev_cpu_load:", cpu_load_list[1])
        print ("random_id:", cpu_load_list[2])

        return 0
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception:
        print('-' * 60)
        print("Exception in user code:")
        traceback.print_exc(file=sys.stdout)
        print('-' * 60)
        return 2

if __name__ == "__main__":
    sys.exit(main())
