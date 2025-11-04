#!/usr/bin/env python3
"""
efer-ip-tracer.py — A fast, cross-platform tracer + IP info viewer
Made by efertechtok
"""

import argparse
import sys
import json
import urllib.request
import socket
import re
import time
from typing import Optional, Dict, Any
from colorama import Fore, Style, init as colorama_init

colorama_init(autoreset=True)

def print_banner() -> None:
    tux = r"""
 .--.
 |o_o |
 |:_/ |
 //   \ \
(|     | )
/'\_   _/\
\___)=(___/
 made by efertechtok and @viperfsfa FOLLOW US ON GITHUB AND TIKTOK!!
    """
    print(Fore.CYAN + tux + Style.RESET_ALL)

IP_LOOKUP_URL = "https://ipapi.co/json/"
TIMEOUT = 10.0

IPV4_RE = re.compile(
    r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}'
    r'(?:25[0-5]|2[0-4]\d|[01]?\d?\d)$'
)
IPV6_RE = re.compile(
    r'^('
    r'(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|'
    r'(?:[0-9a-fA-F]{1,4}:){1,7}:|'
    r'(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}'
    r')$'
)

def is_ip(s: str) -> bool:
    return bool(IPV4_RE.fullmatch(s) or IPV6_RE.fullmatch(s))

def resolve_target(target: str) -> str:
    if is_ip(target):
        return target
    try:
        info = socket.getaddrinfo(target, None, socket.AF_UNSPEC)
        return info[0][4][0]
    except Exception:
        return target

def lookup_ip(ip: str) -> Optional[Dict[str, Any]]:
    url = IP_LOOKUP_URL.format(ip)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.load(resp)
            if data.get("error"):
                return None
            return data
    except Exception as e:
        print(Fore.RED + f"Lookup error: {e}" + Style.RESET_ALL)
        return None
    finally:
        time.sleep(1.2)   # stay under free-tier limit

def print_ip_info(ip: str, info: Optional[Dict[str, Any]]) -> None:
    print(Fore.YELLOW + f"\n== {ip} ==" + Style.RESET_ALL)
    if not info:
        print("No info available or lookup failed.")
        return
    get = lambda k, default="N/A": info.get(k, default)
    print(Fore.GREEN + "Country: " + Style.RESET_ALL + f"{get('country_name')}")
    print(Fore.GREEN + "Region: "  + Style.RESET_ALL + f"{get('region')}")
    print(Fore.GREEN + "City: "    + Style.RESET_ALL + f"{get('city')}")
    print(Fore.GREEN + "Org: "     + Style.RESET_ALL + f"{get('org') or get('asn') or get('asn_org')}")
    print(Fore.GREEN + "Postal: "  + Style.RESET_ALL + f"{get('postal')}")
    print(Fore.GREEN + "Lat/Lon: " + Style.RESET_ALL + f"{get('latitude')}/{get('longitude')}")
    print(Fore.GREEN + "Timezone:" + Style.RESET_ALL + f" {get('timezone')}")
    print(Fore.GREEN + "UTC Off: " + Style.RESET_ALL + f"{get('utc_offset') if get('utc_offset') else get('utc_offset')}")

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

    info = lookup_ip(ip)
    print_ip_info(ip, info)

    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
