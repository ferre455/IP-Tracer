#!/usr/bin/env python3
"""
efer-ip-tracer.py — A fast, cross-platform tracer + IP info viewer
Made by efertechtok (fixed)
"""
import argparse
import sys
import subprocess
import shutil
import platform
import re
import json
import urllib.request
import socket
from typing import List, Optional
from colorama import Fore, Style, init as colorama_init

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

# Regex patterns for IPv4/IPv6
IPV4_RE = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
IPV6_RE = re.compile(r'\b[0-9a-fA-F:]{3,}\b')
IP_LOOKUP_URL = "https://ipapi.co/{}/json/"

def find_traceroute_cmd() -> Optional[str]:
    """Find the correct traceroute/tracepath/tracert command."""
    system = platform.system().lower()
    if system.startswith("win"):
        return "tracert" if shutil.which("tracert") else None
    for cmd in ("traceroute", "tracepath"):
        if shutil.which(cmd):
            return cmd
    return None

def run_traceroute(cmd: str, target: str, max_hops: int = 30) -> List[str]:
    """Run traceroute/tracepath/tracert and return output lines."""
    system = platform.system().lower()
    if system.startswith("win"):
        args = [cmd, "-d", "-h", str(max_hops), target]
    elif cmd == "tracepath":
        args = [cmd, target]
    else:
        args = [cmd, "-n", "-m", str(max_hops), target]

    try:
        completed = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30
        )
        return completed.stdout.splitlines()
    except subprocess.TimeoutExpired:
        print(Fore.RED + "Traceroute timed out (partial/none results)." + Style.RESET_ALL)
        return []
    except Exception as e:
        print(Fore.RED + f"Error running traceroute: {e}" + Style.RESET_ALL)
        return []

def extract_ips_from_lines(lines: List[str]) -> List[str]:
    """Extract unique IPs from traceroute output lines preserving order."""
    seen = set()
    results = []
    for line in lines:
        for m in IPV4_RE.findall(line):
            # Validate each octet is <= 255
            parts = m.split('.')
            if all(0 <= int(p) <= 255 for p in parts):
                if m not in seen:
                    seen.add(m); results.append(m)
        # add IPv6 matches optionally (simple)
        for m in IPV6_RE.findall(line):
            if ':' in m and m not in seen:
                seen.add(m); results.append(m)
    return results#!/usr/bin/env python3
"""
efer-ip-tracer.py — A fast, cross-platform tracer + IP info viewer
Made by efertechtok (fixed)
"""
import argparse
import sys
import subprocess
import shutil
import platform
import re
import json
import urllib.request
import socket
from typing import List, Optional
from colorama import Fore, Style, init as colorama_init

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

# Regex patterns for IPv4/IPv6
IPV4_RE = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
IPV6_RE = re.compile(r'\b[0-9a-fA-F:]{3,}\b')
IP_LOOKUP_URL = "https://ipapi.co/{}/json/"

def find_traceroute_cmd() -> Optional[str]:
    """Find the correct traceroute/tracepath/tracert command."""
    system = platform.system().lower()
    if system.startswith("win"):
        return "tracert" if shutil.which("tracert") else None
    for cmd in ("traceroute", "tracepath"):
        if shutil.which(cmd):
            return cmd
    return None

def run_traceroute(cmd: str, target: str, max_hops: int = 30) -> List[str]:
    """Run traceroute/tracepath/tracert and return output lines."""
    system = platform.system().lower()
    if system.startswith("win"):
        args = [cmd, "-d", "-h", str(max_hops), target]
    elif cmd == "tracepath":
        args = [cmd, target]
    else:
        args = [cmd, "-n", "-m", str(max_hops), target]

    try:
        completed = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30
        )
        return completed.stdout.splitlines()
    except subprocess.TimeoutExpired:
        print(Fore.RED + "Traceroute timed out (partial/none results)." + Style.RESET_ALL)
        return []
    except Exception as e:
        print(Fore.RED + f"Error running traceroute: {e}" + Style.RESET_ALL)
        return []

def extract_ips_from_lines(lines: List[str]) -> List[str]:
    """Extract unique IPs from traceroute output lines preserving order."""
    seen = set()
    results = []
    for line in lines:
        for m in IPV4_RE.findall(line):
            # Validate each octet is <= 255
            parts = m.split('.')
            if all(0 <= int(p) <= 255 for p in parts):
                if m not in seen:
                    seen.add(m); results.append(m)
        # add IPv6 matches optionally (simple)
        for m in IPV6_RE.findall(line):
            if ':' in m and m not in seen:
                seen.add(m); results.append(m)
    return results

def lookup_ip(ip: str, timeout: float = 6.0) -> Optional[dict]:
    url = IP_LOOKUP_URL.format(ip)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.load(resp)
            # ipapi.co returns keys like "error" for failures
            if data.get("error"):
                return None
            return data
    except Exception:
        return None

def print_ip_info(ip: str, info: Optional[dict]) -> None:
    print(Fore.YELLOW + f"\n== {ip} ==" + Style.RESET_ALL)
    if not info:
        print("No info available or lookup failed.")
        return
    get = lambda k, default="N/A": info.get(k, default)
    print(Fore.GREEN + "Country: " + Style.RESET_ALL + f"{get('country_name')}")
    print(Fore.GREEN + "Region:  " + Style.RESET_ALL + f"{get('region')}")
    print(Fore.GREEN + "City:    " + Style.RESET_ALL + f"{get('city')}")
    print(Fore.GREEN + "Org:     " + Style.RESET_ALL + f"{get('org') or get('asn') or get('asn_org')}")
    print(Fore.GREEN + "Postal:  " + Style.RESET_ALL + f"{get('postal')}")
    print(Fore.GREEN + "Lat/Lon: " + Style.RESET_ALL + f"{get('latitude')}/{get('longitude')}")
    print(Fore.GREEN + "Timezone:" + Style.RESET_ALL + f" {get('timezone')}")
    print(Fore.GREEN + "UTC Off: " + Style.RESET_ALL + f"{get('utc_offset') if get('utc_offset') else get('utc_offset')}")
    # short pause not necessary; keep output quick

def resolve_target(target: str) -> str:
    """Return an IP for a hostname, or the same string if it's already an IP."""
    if IPV4_RE.fullmatch(target) or IPV6_RE.fullmatch(target):
        return target
    try:
        return socket.gethostbyname(target)
    except Exception:
        return target

def main() -> int:
    parser = argparse.ArgumentParser(description="efer-ip-tracer: tracer + IP info viewer")
    parser.add_argument("target", nargs="?", help="IP or hostname to trace")
    args = parser.parse_args()

    print_banner()

    if not args.target:
        target = input("Enter target (IP or hostname): ").strip()
    else:
        target = args.target.strip()

    if not target:
        print("No target provided.")
        return 1

    ip = resolve_target(target)
    if ip != target:
        print(Fore.CYAN + f"Resolved {target} -> {ip}" + Style.RESET_ALL)

    cmd = find_traceroute_cmd()
    if not cmd:
        print(Fore.YELLOW + "No traceroute/tracepath/tracert found on system. Skipping traceroute." + Style.RESET_ALL)
        # Still attempt a single IP lookup
        info = lookup_ip(ip)
        print_ip_info(ip, info)
        return 0

    lines = run_traceroute(cmd, ip)
    if not lines:
        # still try one lookup
        info = lookup_ip(ip)
        print_ip_info(ip, info)
        return 0

    # print traceroute output (trim verbose)
    print(Fore.MAGENTA + "\nTraceroute output:" + Style.RESET_ALL)
    for l in lines:
        print(l)

    hops = extract_ips_from_lines(lines)
    if not hops:
        print("\nNo IPs extracted from traceroute.")
        return 0

    # Lookup info for each hop (limit to reasonable amount)
    limit = min(len(hops), 12)
    print(Fore.CYAN + f"\nLooking up first {limit} hops:" + Style.RESET_ALL)
    for hop_ip in hops[:limit]:
        info = lookup_ip(hop_ip)
        print_ip_info(hop_ip, info)

    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")


def lookup_ip(ip: str, timeout: float = 6.0) -> Optional[dict]:
    url = IP_LOOKUP_URL.format(ip)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.load(resp)
            # ipapi.co returns keys like "error" for failures
            if data.get("error"):
                return None
            return data
    except Exception:
        return None

def print_ip_info(ip: str, info: Optional[dict]) -> None:
    print(Fore.YELLOW + f"\n== {ip} ==" + Style.RESET_ALL)
    if not info:
        print("No info available or lookup failed.")
        return
    get = lambda k, default="N/A": info.get(k, default)
    print(Fore.GREEN + "Country: " + Style.RESET_ALL + f"{get('country_name')}")
    print(Fore.GREEN + "Region:  " + Style.RESET_ALL + f"{get('region')}")
    print(Fore.GREEN + "City:    " + Style.RESET_ALL + f"{get('city')}")
    print(Fore.GREEN + "Org:     " + Style.RESET_ALL + f"{get('org') or get('asn') or get('asn_org')}")
    print(Fore.GREEN + "Postal:  " + Style.RESET_ALL + f"{get('postal')}")
    print(Fore.GREEN + "Lat/Lon: " + Style.RESET_ALL + f"{get('latitude')}/{get('longitude')}")
    print(Fore.GREEN + "Timezone:" + Style.RESET_ALL + f" {get('timezone')}")
    print(Fore.GREEN + "UTC Off: " + Style.RESET_ALL + f"{get('utc_offset') if get('utc_offset') else get('utc_offset')}")
    # short pause not necessary; keep output quick

def resolve_target(target: str) -> str:
    """Return an IP for a hostname, or the same string if it's already an IP."""
    if IPV4_RE.fullmatch(target) or IPV6_RE.fullmatch(target):
        return target
    try:
        return socket.gethostbyname(target)
    except Exception:
        return target

def main() -> int:
    parser = argparse.ArgumentParser(description="efer-ip-tracer: tracer + IP info viewer")
    parser.add_argument("target", nargs="?", help="IP or hostname to trace")
    args = parser.parse_args()

    print_banner()

    if not args.target:
        target = input("Enter target (IP or hostname): ").strip()
    else:
        target = args.target.strip()

    if not target:
        print("No target provided.")
        return 1

    ip = resolve_target(target)
    if ip != target:
        print(Fore.CYAN + f"Resolved {target} -> {ip}" + Style.RESET_ALL)

    cmd = find_traceroute_cmd()
    if not cmd:
        print(Fore.YELLOW + "No traceroute/tracepath/tracert found on system. Skipping traceroute." + Style.RESET_ALL)
        # Still attempt a single IP lookup
        info = lookup_ip(ip)
        print_ip_info(ip, info)
        return 0

    lines = run_traceroute(cmd, ip)
    if not lines:
        # still try one lookup
        info = lookup_ip(ip)
        print_ip_info(ip, info)
        return 0

    # print traceroute output (trim verbose)
    print(Fore.MAGENTA + "\nTraceroute output:" + Style.RESET_ALL)
    for l in lines:
        print(l)

    hops = extract_ips_from_lines(lines)
    if not hops:
        print("\nNo IPs extracted from traceroute.")
        return 0

    # Lookup info for each hop (limit to reasonable amount)
    limit = min(len(hops), 12)
    print(Fore.CYAN + f"\nLooking up first {limit} hops:" + Style.RESET_ALL)
    for hop_ip in hops[:limit]:
        info = lookup_ip(hop_ip)
        print_ip_info(hop_ip, info)

    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
