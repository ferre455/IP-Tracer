#!/usr/bin/env python3
import argparse, os, sys, json, subprocess, shutil, time, logging, socket, threading, signal, platform
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Tuple
from ipaddress import ip_address
from colorama import Fore, Style, init as colorama_init

try:
    import curses
    HAS_CURSES = True
except Exception:
    HAS_CURSES = False

try:
    import requests
    HAS_REQUESTS = True
except Exception:
    HAS_REQUESTS = False

colorama_init(autoreset=True)

STOP = threading.Event()

BANNER = r"""
 .--.
 |o_o |
 |:_/ |
 //   \ \
(|     | )
/'\_   _/\
\___)=(___/
 made by efertechtok
"""

DEFAULT_UA = "ip-tracer/1.1 (+https://example.com)"
DEFAULT_PROVIDER = "ipapi"
PROVIDERS = ("ipapi","ipinfo","ipwhois","maxmind","auto")

def is_ip(s: str) -> bool:
    try:
        ip_address(s)
        return True
    except Exception:
        return False

def resolve_host(target: str) -> Optional[str]:
    if STOP.is_set():
        return None
    try:
        info = socket.getaddrinfo(target, None, socket.AF_UNSPEC)
        for fam in (socket.AF_INET, socket.AF_INET6):
            for ai in info:
                if ai[0] == fam:
                    return ai[4][0]
        return info[0][4][0] if info else None
    except Exception:
        return None

def which_tracer() -> Tuple[str,List[str],str]:
    if os.name == "nt":
        cmd = shutil.which("tracert")
        if cmd:
            return cmd, ["-d"], "tracert"
        return "", [], ""
    for c in ("traceroute","tracepath"):
        p = shutil.which(c)
        if p:
            if c == "traceroute":
                return p, ["-n"], "traceroute"
            return p, ["-n"], "tracepath"
    return "", [], ""

def run_traceroute(target: str, max_hops: int, per_hop_timeout: float, overall_timeout: float) -> Tuple[List[Dict[str,Any]], Optional[str]]:
    if STOP.is_set():
        return [], "aborted"
    exe, base, kind = which_tracer()
    if not exe:
        return [], "trace_tool_missing"
    if os.name == "nt":
        args = [exe] + base + ["-h", str(max_hops), "-w", str(int(per_hop_timeout*1000)), target]
    else:
        if kind == "traceroute":
            args = [exe] + base + ["-m", str(max_hops), "-w", str(per_hop_timeout), target]
        else:
            args = [exe] + base + [target]
    try:
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="ignore")
        start = time.time()
        chunks = []
        while True:
            if STOP.is_set():
                try:
                    p.terminate()
                except Exception:
                    pass
                try:
                    p.kill()
                except Exception:
                    pass
                return [], "aborted"
            if overall_timeout and (time.time() - start) > overall_timeout:
                try:
                    p.terminate()
                except Exception:
                    pass
                try:
                    p.kill()
                except Exception:
                    pass
                return [], "trace_timeout"
            line = p.stdout.readline() if p.stdout else ""
            if not line:
                if p.poll() is not None:
                    break
                time.sleep(0.02)
                continue
            chunks.append(line)
        out = "".join(chunks)
    except KeyboardInterrupt:
        return [], "aborted"
    except Exception as e:
        return [], f"trace_failed:{e.__class__.__name__}"
    lines = out.splitlines()
    hops = []
    for line in lines:
        if STOP.is_set():
            return [], "aborted"
        parts = line.strip().split()
        if not parts:
            continue
        hopnum = None
        try:
            hopnum = int(parts[0].strip(":"))
        except Exception:
            pass
        tokens = [p.strip("()[]") for p in parts]
        found_ip = None
        for t in tokens:
            if is_ip(t):
                found_ip = t
                break
        rtts = []
        for t in tokens:
            if t.endswith("ms"):
                try:
                    v = float(t.replace("ms",""))
                    rtts.append(v)
                except Exception:
                    pass
        if hopnum is None and found_ip is None:
            continue
        hops.append({"hop": hopnum, "ip": found_ip, "rtt_ms": rtts[0] if rtts else None, "raw": line})
    filtered = [h for h in hops if h.get("ip")]
    seen = set()
    uniq = []
    for h in filtered:
        ip = h["ip"]
        if ip not in seen:
            seen.add(ip)
            uniq.append(h)
    return uniq, None

def build_proxies(args: argparse.Namespace) -> Dict[str,str]:
    proxies = {}
    if args.tor:
        host = args.tor_host or "127.0.0.1"
        port = str(args.tor_port or 9050)
        uri = f"socks5h://{host}:{port}"
        proxies = {"http": uri, "https": uri}
    if args.http_proxy:
        proxies["http"] = args.http_proxy
    if args.https_proxy:
        proxies["https"] = args.https_proxy
    if args.socks_proxy:
        proxies["http"] = args.socks_proxy
        proxies["https"] = args.socks_proxy
    return proxies

def backoff_sleep(attempt: int, retry_after: Optional[float]) -> None:
    if STOP.is_set():
        return
    if retry_after:
        time.sleep(max(0.0, retry_after))
        return
    time.sleep(min(30, 1.25*(2**attempt)))

def ip_lookup_ipapi(ip: str, session: requests.Session) -> Tuple[Optional[Dict[str,Any]], Optional[str], Optional[float]]:
    if STOP.is_set():
        return None, "aborted", None
    url = f"https://ipapi.co/{ip}/json/"
    r = session.get(url, timeout=(session.timeout, session.timeout))
    ra = None
    try:
        ra = float(r.headers.get("Retry-After")) if r.headers.get("Retry-After") else None
    except Exception:
        ra = None
    if r.status_code != 200:
        return None, f"http_{r.status_code}", ra
    data = r.json()
    if data.get("error"):
        return None, "provider_error", None
    out = {
        "ip": data.get("ip", ip),
        "country": data.get("country_name"),
        "region": data.get("region"),
        "city": data.get("city"),
        "org": data.get("org") or data.get("asn_org"),
        "asn": data.get("asn"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "timezone": data.get("timezone"),
        "utc_offset": data.get("utc_offset"),
        "provider": "ipapi"
    }
    return out, None, None

def ip_lookup_ipinfo(ip: str, session: requests.Session) -> Tuple[Optional[Dict[str,Any]], Optional[str], Optional[float]]:
    if STOP.is_set():
        return None, "aborted", None
    url = f"https://ipinfo.io/{ip}/json"
    r = session.get(url, timeout=(session.timeout, session.timeout))
    ra = None
    try:
        ra = float(r.headers.get("Retry-After")) if r.headers.get("Retry-After") else None
    except Exception:
        ra = None
    if r.status_code != 200:
        return None, f"http_{r.status_code}", ra
    data = r.json()
    org = data.get("org")
    asn = None
    if org and org.startswith("AS"):
        sp = org.split(" ",1)
        asn = sp[0]
        org = sp[1] if len(sp)>1 else None
    lat, lon = None, None
    if data.get("loc"):
        try:
            lat, lon = [float(x) for x in data["loc"].split(",")]
        except Exception:
            pass
    out = {
        "ip": data.get("ip", ip),
        "country": data.get("country"),
        "region": data.get("region"),
        "city": data.get("city"),
        "org": org,
        "asn": asn,
        "latitude": lat,
        "longitude": lon,
        "timezone": data.get("timezone"),
        "utc_offset": None,
        "provider": "ipinfo"
    }
    return out, None, None

def ip_lookup_ipwhois(ip: str, session: requests.Session) -> Tuple[Optional[Dict[str,Any]], Optional[str], Optional[float]]:
    if STOP.is_set():
        return None, "aborted", None
    url = f"https://ipwhois.app/json/{ip}"
    r = session.get(url, timeout=(session.timeout, session.timeout))
    ra = None
    try:
        ra = float(r.headers.get("Retry-After")) if r.headers.get("Retry-After") else None
    except Exception:
        ra = None
    if r.status_code != 200:
        return None, f"http_{r.status_code}", ra
    data = r.json()
    if not data.get("success", True):
        return None, "provider_error", None
    out = {
        "ip": data.get("ip", ip),
        "country": data.get("country"),
        "region": data.get("region"),
        "city": data.get("city"),
        "org": data.get("org") or data.get("isp"),
        "asn": data.get("asn"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "timezone": data.get("timezone"),
        "utc_offset": None,
        "provider": "ipwhois"
    }
    return out, None, None

def ip_lookup_maxmind(ip: str) -> Tuple[Optional[Dict[str,Any]], Optional[str], Optional[float]]:
    if STOP.is_set():
        return None, "aborted", None
    try:
        import geoip2.database
    except Exception:
        return None, "geoip2_unavailable", None
    db_dir = os.environ.get("GEOIP2_DB_DIR") or os.path.expanduser("~/.geoip")
    city_db = os.path.join(db_dir, "GeoLite2-City.mmdb")
    asn_db = os.path.join(db_dir, "GeoLite2-ASN.mmdb")
    if not (os.path.exists(city_db) and os.path.exists(asn_db)):
        return None, "geolite_missing", None
    try:
        with geoip2.database.Reader(city_db) as cr:
            c = cr.city(ip)
            country = c.country.name
            region = None
            if c.subdivisions and len(c.subdivisions) > 0:
                region = c.subdivisions.most_specific.name
            city = c.city.name
            lat = c.location.latitude
            lon = c.location.longitude
            tz = c.location.time_zone
        with geoip2.database.Reader(asn_db) as ar:
            a = ar.asn(ip)
            asn = f"AS{a.autonomous_system_number}" if a.autonomous_system_number else None
            org = a.autonomous_system_organization
        out = {"ip": ip,"country": country,"region": region,"city": city,"org": org,"asn": asn,"latitude": lat,"longitude": lon,"timezone": tz,"utc_offset": None,"provider":"maxmind"}
        return out, None, None
    except Exception:
        return None, "geolite_lookup_failed", None

def new_session(args: argparse.Namespace) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": args.user_agent, "Accept": "application/json"})
    s.proxies = build_proxies(args)
    s.verify = True
    s.timeout = args.http_timeout
    return s

def lookup_ip(ip: str, args: argparse.Namespace, session: Optional[requests.Session]) -> Dict[str,Any]:
    if args.no_lookup or STOP.is_set():
        return {"ip": ip}
    providers = []
    if args.provider == "auto":
        providers = ["maxmind","ipapi","ipwhois","ipinfo"]
    else:
        providers = [args.provider]
    attempt = 0
    while attempt < 6 and not STOP.is_set():
        attempt += 1
        p = providers[0] if providers else DEFAULT_PROVIDER
        if p == "maxmind":
            data, err, ra = ip_lookup_maxmind(ip)
        else:
            if not HAS_REQUESTS:
                return {"ip": ip, "error": "requests_missing"}
            if session is None:
                session = new_session(args)
            if p == "ipapi":
                data, err, ra = ip_lookup_ipapi(ip, session)
            elif p == "ipinfo":
                data, err, ra = ip_lookup_ipinfo(ip, session)
            else:
                data, err, ra = ip_lookup_ipwhois(ip, session)
        if data:
            return data
        if err in ("aborted",):
            return {"ip": ip, "error": "aborted"}
        if err in ("geoip2_unavailable","geolite_missing"):
            if len(providers) > 1:
                providers.pop(0)
                continue
            return {"ip": ip, "error": err}
        if err and err.startswith("http_"):
            backoff_sleep(attempt, ra)
            if len(providers) > 1:
                providers.append(providers.pop(0))
            continue
        if err in ("provider_error","geolite_lookup_failed"):
            if len(providers) > 1:
                providers.pop(0)
                continue
            return {"ip": ip, "error": err}
    return {"ip": ip, "error": "lookup_failed"}

def whois_lookup(ip: str, timeout: float) -> Optional[str]:
    if STOP.is_set():
        return None
    exe = shutil.which("whois")
    if not exe:
        return None
    try:
        r = subprocess.run([exe, ip], capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=timeout)
        return r.stdout
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None

def print_banner(mode: str, use_color: bool):
    if mode == "never":
        return
    if mode == "always":
        s = BANNER
    else:
        if not sys.stdout.isatty():
            return
        s = BANNER
    if use_color:
        print(Fore.CYAN + s + Style.RESET_ALL)
    else:
        print(s)

def colorize(s: str, color: str, use_color: bool) -> str:
    if not use_color:
        return s
    return getattr(Fore, color) + s + Style.RESET_ALL

def print_table(rows: List[Dict[str,Any]], use_color: bool):
    cols = ["hop","ip","country","region","city","asn","org","lat","lon","rtt_ms"]
    header = ["HOP","IP","COUNTRY","REGION","CITY","ASN","ORG","LAT","LON","RTT(ms)"]
    data = []
    for r in rows:
        g = r.get("geo",{})
        data.append([
            r.get("hop"),
            r.get("ip"),
            g.get("country"),
            g.get("region"),
            g.get("city"),
            g.get("asn"),
            g.get("org"),
            g.get("latitude"),
            g.get("longitude"),
            r.get("rtt_ms")
        ])
    widths = [len(h) for h in header]
    for row in data:
        for i, v in enumerate(row):
            widths[i] = max(widths[i], len(str(v)) if v is not None else 0)
    line = "  ".join(h.ljust(widths[i]) for i,h in enumerate(header))
    print(colorize(line, "YELLOW", use_color))
    for row in data:
        s = "  ".join((str(v) if v is not None else "").ljust(widths[i]) for i,v in enumerate(row))
        print(colorize(s, "GREEN", use_color))

def gather_targets(args: argparse.Namespace) -> List[str]:
    targets = []
    if args.targets:
        targets.extend(args.targets)
    if args.batch_file:
        with (sys.stdin if args.batch_file == "-" else open(args.batch_file, "r", encoding="utf-8")) as f:
            for line in f:
                if STOP.is_set():
                    break
                t = line.strip()
                if t:
                    targets.append(t)
    if not targets and not args.tui:
        if sys.stdin.isatty():
            try:
                t = input("Target (blank to end): ").strip()
                while t and not STOP.is_set():
                    targets.append(t)
                    t = input("Target (blank to end): ").strip()
            except KeyboardInterrupt:
                pass
        else:
            for line in sys.stdin:
                if STOP.is_set():
                    break
                t = line.strip()
                if t:
                    targets.append(t)
    return targets

def process_target(target: str, args: argparse.Namespace, session: Optional[requests.Session]) -> Dict[str,Any]:
    if STOP.is_set():
        return {"target": target, "error": "aborted"}
    out: Dict[str,Any] = {"target": target, "hops": []}
    dest = target if is_ip(target) else resolve_host(target)
    out["resolved_ip"] = dest
    if dest is None:
        out["error"] = "resolve_failed"
        return out
    hops, terr = ([], None)
    if not args.no_traceroute:
        overall = args.trace_timeout or max(10.0, min(120.0, args.max_hops * max(0.5, args.hop_timeout) * 2.0))
        hops, terr = run_traceroute(target, args.max_hops, args.hop_timeout, overall)
    if STOP.is_set():
        return {"target": target, "error": "aborted"}
    if args.no_traceroute or not hops:
        hops = [{"hop": 1, "ip": dest, "rtt_ms": None, "raw": None}]
        if terr:
            out["trace_error"] = terr
    uniq_ips = []
    seen = set()
    for h in hops:
        ip = h["ip"]
        if ip and ip not in seen:
            seen.add(ip)
            uniq_ips.append(h)
    def do_lookup(h):
        if STOP.is_set():
            return {"hop": h.get("hop"), "ip": h.get("ip"), "rtt_ms": h.get("rtt_ms"), "geo": {"ip": h.get("ip"), "error": "aborted"}}
        ip = h["ip"]
        geo = lookup_ip(ip, args, session)
        r = {"hop": h.get("hop"), "ip": ip, "rtt_ms": h.get("rtt_ms"), "geo": geo}
        if args.whois and ip and not STOP.is_set():
            w = whois_lookup(ip, args.whois_timeout)
            r["whois"] = w
        return r
    rows: List[Dict[str,Any]] = []
    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        futs = [ex.submit(do_lookup, h) for h in uniq_ips]
        try:
            for f in as_completed(futs, timeout=args.lookup_pool_timeout):
                if STOP.is_set():
                    break
                rows.append(f.result())
        except KeyboardInterrupt:
            STOP.set()
        except Exception:
            pass
        finally:
            ex.shutdown(wait=False, cancel_futures=True)
    rows.sort(key=lambda x: (x["hop"] if isinstance(x["hop"], int) else 1e9))
    out["hops"] = rows
    return out

def print_results(res: Dict[str,Any], args: argparse.Namespace):
    if args.json:
        print(json.dumps(res, ensure_ascii=False))
        return
    hdr = f"== {res.get('target','')} =="
    if res.get("resolved_ip") and res["resolved_ip"] != res.get("target"):
        hdr += f" -> {res['resolved_ip']}"
    print(colorize(hdr, "CYAN", not args.no_color))
    if res.get("error"):
        print(colorize(f"error: {res['error']}", "RED", not args.no_color))
        return
    print_table(res.get("hops", []), not args.no_color)

def run_cli(args: argparse.Namespace):
    print_banner(args.banner, not args.no_color)
    targets = gather_targets(args)
    if STOP.is_set():
        sys.exit(130)
    if not targets:
        print("no targets")
        sys.exit(2)
    session = new_session(args) if HAS_REQUESTS else None
    for t in targets:
        if STOP.is_set():
            break
        res = process_target(t, args, session)
        print_results(res, args)

def tui_screen(stdscr, args: argparse.Namespace):
    curses.curs_set(1)
    stdscr.nodelay(False)
    h, w = stdscr.getmaxyx()
    def draw_center(y, text):
        x = max(0, (w - len(text)) // 2)
        stdscr.addstr(y, x, text[:max(0,w-2)])
    curses.echo()
    while not STOP.is_set():
        stdscr.clear()
        draw_center(1, "ip-tracer TUI")
        draw_center(3, "Enter target and press Enter. F10 to exit.")
        stdscr.addstr(5, 2, "Target: ".ljust(w-2))
        stdscr.move(5, 10)
        try:
            raw = stdscr.getstr(5, 10, 256)
        except KeyboardInterrupt:
            return
        if raw is None:
            continue
        t = raw.decode(errors="ignore").strip()
        if not t:
            continue
        stdscr.clear()
        draw_center(1, f"Tracing {t} ...")
        stdscr.refresh()
        session = new_session(args) if HAS_REQUESTS else None
        res = process_target(t, args, session)
        y = 3
        hdr = f"{t}"
        if res.get("resolved_ip") and res["resolved_ip"] != t:
            hdr += f" -> {res['resolved_ip']}"
        stdscr.addstr(y, 2, hdr[:w-4]); y += 1
        headers = ["HOP","IP","COUNTRY","REGION","CITY","ASN","ORG","LAT","LON","RTT"]
        stdscr.addstr(y, 2, "  ".join(headers)[:w-4]); y += 1
        for r in res.get("hops", []):
            if y >= h-2:
                stdscr.addstr(h-2, 2, "Press any key to continue...")
                stdscr.getch()
                stdscr.clear()
                y = 3
            g = r.get("geo",{})
            row = [
                str(r.get("hop") or ""),
                r.get("ip") or "",
                str(g.get("country") or ""),
                str(g.get("region") or ""),
                str(g.get("city") or ""),
                str(g.get("asn") or ""),
                str(g.get("org") or ""),
                str(g.get("latitude") or ""),
                str(g.get("longitude") or ""),
                str(r.get("rtt_ms") or "")
            ]
            stdscr.addstr(y, 2, "  ".join(row)[:w-4])
            y += 1
        stdscr.addstr(h-2, 2, "F10 exit | Any key new query")
        k = stdscr.getch()
        if k == curses.KEY_F10:
            break

def run_tui(args: argparse.Namespace):
    if not HAS_CURSES:
        print("tui unavailable")
        sys.exit(3)
    try:
        curses.wrapper(tui_screen, args)
    except KeyboardInterrupt:
        pass

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="ip_tracer")
    p.add_argument("targets", nargs="*", help="targets (IP or hostname)")
    p.add_argument("--batch-file", help="file with one target per line, or '-' for stdin")
    p.add_argument("--no-traceroute", action="store_true")
    p.add_argument("--no-lookup", action="store_true")
    p.add_argument("--whois", action="store_true")
    p.add_argument("--provider", choices=PROVIDERS, default=DEFAULT_PROVIDER)
    p.add_argument("--user-agent", default=DEFAULT_UA)
    p.add_argument("--http-timeout", type=float, default=10.0)
    p.add_argument("--lookup-pool-timeout", type=float, default=60.0)
    p.add_argument("--max-hops", type=int, default=30)
    p.add_argument("--hop-timeout", type=float, default=2.0)
    p.add_argument("--trace-timeout", type=float, default=0.0)
    p.add_argument("--threads", type=int, default=max(4, min(32, (os.cpu_count() or 4)*5)))
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-color", action="store_true")
    p.add_argument("--banner", choices=("never","auto","always"), default="never")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--log-file")
    p.add_argument("--tui", action="store_true")
    p.add_argument("--tor", action="store_true")
    p.add_argument("--tor-host")
    p.add_argument("--tor-port", type=int)
    p.add_argument("--http-proxy")
    p.add_argument("--https-proxy")
    p.add_argument("--socks-proxy")
    p.add_argument("--whois-timeout", type=float, default=10.0)
    args = p.parse_args()
    lvl = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(filename=args.log_file, level=lvl, format="%(asctime)s %(levelname)s %(message)s")
    return args

def _sigint(signum, frame):
    if STOP.is_set():
        os._exit(130)
    STOP.set()
    try:
        sys.stderr.write("\n^C\n")
        sys.stderr.flush()
    except Exception:
        pass
    def force():
        time.sleep(1.0)
        os._exit(130)
    threading.Thread(target=force, daemon=True).start()
    raise KeyboardInterrupt

def main():
    signal.signal(signal.SIGINT, _sigint)
    if hasattr(signal, "SIGTERM"):
        try:
            signal.signal(signal.SIGTERM, _sigint)
        except Exception:
            pass
    args = parse_args()
    if args.tui:
        run_tui(args)
        if STOP.is_set():
            sys.exit(130)
        sys.exit(0)
    run_cli(args)
    if STOP.is_set():
        sys.exit(130)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
