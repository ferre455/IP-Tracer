# Description

This is a small cross-platform Python traceroute + IP lookup tool that:

* runs a traceroute (uses `traceroute` / `tracepath` on Unix-like systems and `tracert` on Windows),
* extracts IP addresses per hop,
* performs IP geolocation lookups (uses a public IP geolocation API),
* prints a neat, colored table to the terminal,
* includes a small ASCII Tux banner: `made by efertechtok`.

It requires Python 3 and the Python package `colorama`. On Linux/macOS the script uses the system `traceroute`/`tracepath` command; on Windows it uses the built-in `tracert`.

---

## Requirements

* Python 3.8+ recommended (Python 3.6+ should work)
* `pip` (or `pip3`) to install Python packages
* Terminal with ANSI color support (most terminals do)
* One of: `traceroute` or `tracepath` on Linux/macOS (Windows has `tracert` built-in)
* Network connectivity for IP lookups (script uses a public geolocation API by default)

Optional but recommended:

* `whois` (if you want WHOIS lookups)
* a Python virtual environment for isolation

---

## Prepare the script (one-time)

1. Save your script file (the clean, organized version you use) as `ip_tracer.py`.
2. Make it executable on Unix-like systems:

```bash
chmod +x ip_tracer.py
```

---

## Python dependency (all platforms)

Create a venv (recommended) and install `colorama`:

```bash
# create & activate venv (optional but recommended)
python3 -m venv venv
# Unix/macOS:
source venv/bin/activate
# Windows (PowerShell):
venv\Scripts\Activate.ps1

# install dependency
pip install --upgrade pip
pip install colorama
```

If you prefer a system install:

```bash
pip3 install --user colorama
```

---

## System packages by platform / distro

> Note: package names sometimes vary by distribution/version. If a command below fails, you can search the package index for `traceroute` or `tracepath` (e.g. `apt search traceroute`). The script will automatically pick `traceroute` / `tracepath` / `tracert` that is present on PATH.

### Debian / Ubuntu / Linux Mint

Install traceroute (and optionally whois):

```bash
sudo apt update
sudo apt install -y traceroute whois
```

If you prefer `tracepath` and it's not present, install `iputils`/`iproute2` equivalent (if your distro provides `tracepath` in a specific package), otherwise `traceroute` is fine.

### Fedora / CentOS / RHEL

On Fedora:

```bash
sudo dnf install -y traceroute whois
```

On CentOS/RHEL (7/8) you can use `yum`/`dnf` similarly; you may need EPEL for some packages:

```bash
sudo yum install -y traceroute whois
# or, on newer systems
sudo dnf install -y traceroute whois
```

### Arch Linux / Manjaro

Arch normally packages traceroute utilities—install `inetutils` or the `traceroute` package:

```bash
sudo pacman -Syu
sudo pacman -S --needed inetutils whois
```

If `traceroute` is available as a separate package on your mirror, use that.

### openSUSE

```bash
sudo zypper refresh
sudo zypper install -y traceroute whois
```

### Alpine Linux

```bash
sudo apk update
# traceroute might be in iputils or busybox; try:
sudo apk add traceroute whois
# if traceroute not found, try installing iputils or busybox-extras
```

### macOS

macOS usually includes `traceroute` by default. If you use Homebrew and want additional utilities:

```bash
# optional
brew update
# install inetutils (provides GNU versions)
brew install inetutils
# install whois if desired
brew install whois
```

### Windows (10 / 11)

* `tracert` is built in — no traceroute installation needed.
* Install Python from the Microsoft Store or python.org and ensure `python` / `pip` are on PATH.
* Install `colorama`:

```powershell
python -m pip install --upgrade pip
python -m pip install colorama
```

* (Optional) Install `whois` equivalent or use online WHOIS web tools. Chocolatey users:

```powershell
choco install -y python
choco install -y whois
```

---

## Run the script

Examples:

```bash
# with venv activated (Unix/macOS)
python ip_tracer.py 8.8.8.8
python ip_tracer.py example.com
python ip_tracer.py 1.1.1.1 --max-hops 20
python ip_tracer.py 8.8.8.8 --no-lookup   # skip geolocation lookups
```

On Windows (PowerShell/CMD):

```powershell
python ip_tracer.py 8.8.8.8
```

---

## Common troubleshooting

* **“No traceroute/tracert command found on PATH.”**
  Install `traceroute`/`tracepath` (see distro instructions above). On Windows use `tracert`.

* **Script shows `lookup error: True` for 192.168.x.x or 10.x.x.x**
  Those are private LAN addresses — geolocation APIs won’t return public location info for RFC1918 addresses. That’s expected.

* **Color codes appear as raw escape characters on Windows PowerShell**
  Use a modern terminal (Windows Terminal, Command Prompt, or PowerShell 7) or ensure `colorama` is installed and terminal supports ANSI. If issues persist, run in Git Bash, Windows Terminal, or enable VT100 support in older consoles.

* **Slow lookups / rate limiting**
  Public geolocation APIs often rate-limit. Use `--no-lookup` for fast traceroute-only runs, add a larger delay between lookups, or use an API key from a paid provider if you need heavy usage.

* **DNS names instead of IPs**
  The script uses `-n`/`-d` flags to avoid slow DNS resolution and keep parsing stable. If you want names, remove those flags in `run_traceroute()` (but parsing might require adjustments).

---

## Security, privacy & ethics

* The script returns aggregate/public info from IP geolocation databases (city/ISP/ASN). It **won’t** give a private person’s street address. Don’t use it to attempt to identify or harass individuals.
* Use the tool only on servers you control, public infrastructure, or for educational purposes on known targets (e.g., `8.8.8.8`, `1.1.1.1`, your own IP).
* If you build automation that repeatedly queries public IP APIs, follow the API terms and rate limits.
