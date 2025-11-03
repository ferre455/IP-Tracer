#!/usr/bin/env python3
import sys
import subprocess
import shutil
import platform
import re
import json
import urllib.request
import urllib.error
from time import sleep
from colorama import init as colorama_init, Fore, Style

colorama_init(autoreset=True)

def print_banner():
    tux = r"""
        .--.  
       |o_o | 
       |:_/ | 
      //   \ \ 
     (|     | )
    /'\_   _/`\
    \___)=(___/

     made by efertechtok
    """
    print(Fore.CYAN + tux + Style.RESET_ALL)

TRACEROUTE_CMD_POSIX = "traceroute"
TRACEROUTE_CMD_WIN = "tracert"

IPV4_RE = re.compile(r'(\d{1,3}(?:\.\d{1,3}){3})')
IPV6_RE = re.compile(r'([0-9a-fA-F:]{3,})')
IP_LOOKUP_URL = "https://ipapi.co/{ip}/json/"

def find_traceroute_cmd():
    if platform.system().lower().startswith("win"):
        cmd = TRACEROUTE_CMD_WIN
    else:
        for candidate in (TRACEROUTE_CMD_POSIX, "tracepath"):
            if shutil.which(candidate):
                return candidate
        cmd = TRACEROUTE_CMD_POSIX
    return cmd if shutil.which(cmd) else None

def run_traceroute(cmd, target, max_hops=30, timeout=None):
    system = platform.system().lower()
    if system.startswith("win"):
        args = [cmd, "-d", "-h", str(max_hops), target]
    else:
        args = [cmd, "-n", "-m", str(max_hops), target] if cmd != "tracepath" else [cmd, "-n", target]
    try:
        completed = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        return completed.stdout.splitlines()
    except Exception as e:
        print(Fore.RED + f"Failed to run traceroute: {e}")
        return []

def extract_ips(line):
    ips = IPV4_RE.findall(line)
    if ips:
        return ips
    ipv6 = [x for x in IPV6_RE.findall(line) if ":" in x]
    return ipv6

def lookup_ip_info(ip, timeout=8):
    url = IP_LOOKUP_URL.format(ip=ip)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ip_tracer/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {"error": True}

def is_private_ip(ip):
    private_blocks = ("10.", "172.16.", "172.17.", "172.18.", "172.19.",
                      "172.20.", "172.21.", "172.22.", "172.23.",
                      "172.24.", "172.25.", "172.26.", "172.27.",
                      "172.28.", "172.29.", "172.30.", "172.31.", "192.168.")
    return ip.startswith(private_blocks)

def pretty_print_table(hops):
    print()
    header = f"{Fore.MAGENTA}{'Hop':<5}{'IP Address':<20}{'City':<20}{'Region':<20}{'Country':<20}{'Organization'}{Style.RESET_ALL}"
    print(header)
    print(Fore.MAGENTA + "-" * 100 + Style.RESET_ALL)
    for hop_no, ip, info in hops:
        if not ip:
            continue

        if info is None or "error" in info:
            if is_private_ip(ip):
                city = region = country = "Local Network"
                org = ""
            else:
                city = region = country = "Lookup failed"
                org = ""
        else:
            city = info.get("city", "") or "-"
            region = info.get("region", "") or "-"
            country = info.get("country_name", "") or "-"
            org = info.get("org", "") or "-"

        print(f"{Fore.CYAN}{hop_no:<5}{Fore.GREEN}{ip:<20}{Fore.YELLOW}{city:<20}{region:<20}{country:<20}{Fore.WHITE}{org}{Style.RESET_ALL}")
    print()
    print(Fore.MAGENTA + "-" * 100 + Style.RESET_ALL)

def main():
    print_banner()

    if len(sys.argv) < 2:
        print("Usage: python ip_tracer.py <target> [--max-hops N] [--no-lookup]")
        sys.exit(1)

    target = sys.argv[1]
    max_hops = 30
    do_lookup = True
    if "--max-hops" in sys.argv:
        try:
            max_hops = int(sys.argv[sys.argv.index("--max-hops") + 1])
        except Exception:
            pass
    if "--no-lookup" in sys.argv:
        do_lookup = False

    cmd = find_traceroute_cmd()
    if not cmd:
        print(Fore.RED + "No traceroute/tracert command found on PATH.")
        sys.exit(2)

    print(Style.BRIGHT + Fore.MAGENTA + f"Running traceroute ({cmd}) to {target} (max hops: {max_hops})...\n" + Style.RESET_ALL)
    lines = run_traceroute(cmd, target, max_hops=max_hops)
    if not lines:
        print(Fore.RED + "Traceroute returned no output.")
        sys.exit(3)

    hops = []
    hop_no = 0
    for line in lines:
        hop_no += 1
        ips = extract_ips(line)
        ip = ips[0] if ips else None
        info = None
        if ip and do_lookup:
            if is_private_ip(ip):
                # treat private IPs as local network without performing lookup
                info = None
            else:
                info = lookup_ip_info(ip)
                # be courteous to the lookup service
                sleep(0.1)
        hops.append((hop_no, ip, info))

    pretty_print_table(hops)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + Fore.RED + "Interrupted by user." + Style.RESET_ALL)
        sys.exit(4)