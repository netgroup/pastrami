#!/usr/bin/env python3
import os
import yaml
import json
import subprocess
import sys

CONFIG_PATH = 'config_sut.yml'
TARGETS = {'port1': 'enp6s0f0', 'port2': 'enp6s0f1'}  # Desired final interface names on the SUT

def sh(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout

def find_dev_by_name_or_alt(wanted):
    # Returns the actual existing interface name.
    # Tries a direct lookup first; if not found, searches in altnames.
    try:
        subprocess.run(['ip', 'link', 'show', 'dev', wanted], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return wanted
    except subprocess.CalledProcessError:
        pass
    # Search in altnames
    data = sh(['bash','-lc',"ip -j -d link"]).strip()
    links = json.loads(data or "[]")
    for l in links:
        if 'altnames' in l and l['altnames']:
            if wanted in l['altnames']:
                return l['ifname']
    return None

def dev_exists(name):
    return subprocess.run(['ip','link','show','dev',name],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

def rename(old_name, new_name):
    if old_name == new_name:
        print(f"[=] {old_name} already named {new_name}, skip.")
        return
    if dev_exists(new_name):
        print(f"[!] Dest name {new_name} already exists, skip.")
        return
    try:
        subprocess.run(['ip','link','set',old_name,'down'], check=True)
        subprocess.run(['ip','link','set',old_name,'name',new_name], check=True)
        subprocess.run(['ip','link','set',new_name,'up'], check=True)
        print(f"[+] Renamed {old_name} → {new_name}")
    except subprocess.CalledProcessError as e:
        print(f"[!] Failed to rename {old_name} → {new_name}: {e}")

def main():
    with open(CONFIG_PATH,'r') as f:
        cfg = yaml.safe_load(f) or {}
    ifaces = (cfg.get('interfaces') or {})
    for k, dest in TARGETS.items():
        src_wanted = ifaces.get(k)
        if not src_wanted:
            print(f"[!] Missing interfaces.{k} in {CONFIG_PATH}, skip.")
            continue
        real = find_dev_by_name_or_alt(src_wanted)
        if not real:
            print(f"[!] Interface {src_wanted} not found (name/altname), skip.")
            continue
        rename(real, dest)

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("[!] Run as root (sudo).")
        sys.exit(1)
    import os
    main()
