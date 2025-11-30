#!/usr/bin/env python3
# encoding: utf-8
"""
One-click runner:
- Runs local TG prep scripts
- SSH into SUT as root and runs SUT scripts
- Comes back to TG and runs TRex + experiment
Path handling is dynamic: we use the directory of THIS script on both sides.
"""

import os
import sys
import yaml
import paramiko
import subprocess

CONFIG_PATH = 'config.yml'


def load_cfg():
    """Load YAML config from CONFIG_PATH."""
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f) or {}


def run_local(cmd):
    """Run a local command and raise on failure."""
    print(f"[LOCAL] $ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def load_private_key(pkey_path: str):
    """
    Load an SSH private key for Paramiko.
    Tries RSA first; if that fails, tries Ed25519.
    """
    try:
        return paramiko.RSAKey.from_private_key_file(pkey_path)
    except paramiko.ssh_exception.SSHException:
        return paramiko.Ed25519Key.from_private_key_file(pkey_path)


def run_remote(ip: str, port: int, user: str, pkey_path: str, command: str):
    """
    Execute a remote command via SSH using Paramiko.
    Prints stdout/stderr and raises on non-zero exit code.
    """
    print(f"[REMOTE {user}@{ip}] $ {command}")
    key = load_private_key(pkey_path)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=ip,
        port=port,
        username=user,
        pkey=key,
        timeout=30,
        allow_agent=False,
        look_for_keys=False,
    )

    stdin, stdout, stderr = ssh.exec_command(command)

    # Stream outputs
    out = stdout.read().decode(errors='ignore')
    err = stderr.read().decode(errors='ignore')
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip())

    rc = stdout.channel.recv_exit_status()
    ssh.close()

    if rc != 0:
        raise subprocess.CalledProcessError(rc, command)


def main():
    print("🚀 One-Click starting...\n")
    cfg = load_cfg()

    # SUT connection parameters from config.yml
    sut_ip   = cfg.get('IP_REMOTE')                   # REQUIRED
    sut_port = int(cfg.get('SSH_PORT', 22))           # optional, default 22
    sut_user = cfg.get('SUT_SSH_USER', 'root')        # default: root
    pkey     = cfg.get('PRIVATE_KEY', '/root/.ssh/id_rsa')

    if not sut_ip:
        print("[ERR] IP_REMOTE not set in config.yml")
        sys.exit(1)
    if not os.path.exists(pkey):
        print(f"[ERR] PRIVATE_KEY not found: {pkey}")
        sys.exit(1)

    # Dynamic script directory (used both locally and remotely).
    # Assumes the project is checked out at the same relative path on SUT.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    remote_cd = f'cd {script_dir}'

    try:
        # 1) TG: rename interfaces
        run_local(['sudo', 'python3', os.path.join(script_dir, 'rename_interface.py')])

        # 2) TG: setup TG
        run_local(['sudo', os.path.join(script_dir, 'setup_tg.sh')])

        # 3) SUT: rename interfaces (run in the same directory on SUT)
        run_remote(sut_ip, sut_port, sut_user, pkey, f'{remote_cd} && python3 rename_interface_sut.py')

        # 4) SUT: setup SUT (sudo is fine even if root)
        run_remote(sut_ip, sut_port, sut_user, pkey, f'{remote_cd} && sudo ./setup_sut.sh')

        # 5) TG: start TRex
        run_local(['sudo', os.path.join(script_dir, 'trex_run_fin.sh')])

        # 6) TG: run experiment
        run_local(['sudo', 'python3', os.path.join(script_dir, 'experiment-run-yaml.py')])

        print("\n🎉 DONE.")
    except subprocess.CalledProcessError as e:
        print(f"\n[FAIL] Command failed: {e}")
        sys.exit(e.returncode)


if __name__ == '__main__':
    main()
