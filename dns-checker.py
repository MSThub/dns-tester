import subprocess
import requests
import time
import sys
import os
import re
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
INTERFACE_NAME: Optional[str] = None
DNS_FILE: str = "dns_list.txt"
TIMEOUT: int = 7
VERIFY_RETRIES: int = 5
RETRY_DELAY: float = 1.0

# ─────────────────────────────────────────────
# Console Utilities
# ─────────────────────────────────────────────
def enable_ansi() -> None:
    """Enable ANSI escape sequences on Windows."""
    os.system("")

def clear_screen() -> None:
    """Clear the entire terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")

def clear_current_line() -> None:
    """Clear the current line in the terminal."""
    sys.stdout.write("\033[2K\r")
    sys.stdout.flush()

def clear_previous_line() -> None:
    """Clear the previous line in the terminal."""
    sys.stdout.write("\033[1A\033[2K")
    sys.stdout.flush()

# ─────────────────────────────────────────────
# Network Interface Helpers
# ─────────────────────────────────────────────
def get_network_interfaces() -> List[str]:
    """Return a list of enabled network interface names."""
    result = subprocess.run(
        "netsh interface show interface",
        shell=True,
        capture_output=True,
        text=True,
    )
    interfaces = []
    for line in result.stdout.splitlines():
        if "Connected" in line or "Disconnected" in line:
            parts = line.split()
            if len(parts) >= 4:
                interfaces.append(" ".join(parts[3:]))
    return interfaces

def select_interface() -> bool:
    """Let the user choose a network interface."""
    global INTERFACE_NAME

    interfaces = get_network_interfaces()
    if not interfaces:
        print("[!] No network interfaces found.")
        return False

    print("\nAvailable Network Interfaces:\n")
    for idx, iface in enumerate(interfaces, start=1):
        print(f"  {idx}. {iface}")

    while True:
        try:
            choice = int(input("\nSelect interface: "))
            if 1 <= choice <= len(interfaces):
                INTERFACE_NAME = interfaces[choice - 1]
                return True
            print("[!] Invalid selection. Please enter a number between 1 and", len(interfaces))
        except ValueError:
            print("[!] Please enter a valid number.")

# ─────────────────────────────────────────────
# DNS Operations
# ─────────────────────────────────────────────
def set_dns(primary: str, secondary: Optional[str]) -> bool:
    """Set primary and optional secondary DNS on the selected interface."""
    try:
        subprocess.run(
            f'netsh interface ip set dns name="{INTERFACE_NAME}" static {primary} primary',
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if secondary:
            subprocess.run(
                f'netsh interface ip add dns name="{INTERFACE_NAME}" {secondary} index=2',
                shell=True,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        subprocess.run(
            "ipconfig /flushdns",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False

def reset_dns_to_auto() -> None:
    """Revert DNS settings to DHCP (automatic)."""
    subprocess.run(
        f'netsh interface ip set dns name="{INTERFACE_NAME}" dhcp',
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def verify_dns(primary: str) -> Tuple[bool, str]:
    """Verify that the DNS is applied and can resolve a domain."""
    result = subprocess.run(
        f'netsh interface ip show dns name="{INTERFACE_NAME}"',
        shell=True,
        capture_output=True,
        text=True,
    )
    if primary not in result.stdout:
        return False, "DNS not applied on interface"

    try:
        result = subprocess.run(
            f"nslookup google.com {primary}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout.lower()
        if "timed out" in output or "unreachable" in output:
            return False, "DNS not responding"
        if "can't find" in output or "servfail" in output:
            return False, "DNS resolution failed"
        return True, "OK"
    except subprocess.TimeoutExpired:
        return False, "DNS query timeout"
    except Exception:
        return False, "Unknown error"

# ─────────────────────────────────────────────
# Network Utilities
# ─────────────────────────────────────────────
def check_url(url: str) -> Tuple[bool, Optional[int]]:
    """Check if a URL is reachable (HTTP status < 400)."""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        response = requests.get(url, timeout=TIMEOUT)
        return response.status_code < 400, response.status_code
    except (requests.ConnectionError, requests.Timeout, Exception):
        return False, None

def get_ping(ip: str) -> Optional[str]:
    """Ping an IP and return the response time in ms, or None."""
    try:
        result = subprocess.run(
            f"ping -n 1 {ip}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        match = re.search(r"time[=<](\d+)ms", result.stdout, re.IGNORECASE)
        return f"{match.group(1)}ms" if match else None
    except Exception:
        return None

# ─────────────────────────────────────────────
# DNS List Parsing
# ─────────────────────────────────────────────
def parse_dns_file(path: str) -> List[Dict[str, Any]]:
    """Parse a DNS list file."""
    entries = []
    with open(path, encoding="utf-8") as file:
        for line_no, raw_line in enumerate(file, 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [part.strip() for part in line.split(",")]
            primary = parts[0]
            secondary = parts[1] if len(parts) > 1 and parts[1] else None
            name = parts[2] if len(parts) > 2 and parts[2] else primary

            if not primary:
                print(f"[!] Line {line_no} skipped: empty primary")
                continue

            entries.append({
                "primary": primary,
                "secondary": secondary,
                "name": name,
            })
    return entries

def load_dns_list() -> Optional[List[Dict[str, Any]]]:
    """Load DNS list from the default file."""
    try:
        dns_list = parse_dns_file(DNS_FILE)
    except FileNotFoundError:
        print(f"\n[!] File not found: {DNS_FILE}")
        return None

    if not dns_list:
        print("[!] DNS list is empty.")
        return None

    return dns_list

# ─────────────────────────────────────────────
# DNS Testing
# ─────────────────────────────────────────────
def test_dns_entry(
    entry: Dict[str, Any],
    target_url: str,
    index: int,
    total: int,
    results: List[Dict[str, Any]],
) -> None:
    """Test a single DNS entry and store the result."""
    label = entry["name"]
    primary = entry["primary"]
    secondary = entry["secondary"]

    print(f"[{index}/{total}] Testing {label}...", end="\r")
    sys.stdout.flush()

    if not set_dns(primary, secondary):
        clear_current_line()
        print(f"  \033[31m✗\033[0m  {label:<20}  {primary:<16}  → DNS set failed")
        results.append({
            "name": label,
            "primary": primary,
            "secondary": secondary,
            "ok": False,
        })
        return

    verified = False
    reason = ""
    for _ in range(VERIFY_RETRIES):
        verified, reason = verify_dns(primary)
        if verified:
            break
        time.sleep(RETRY_DELAY)

    if not verified:
        clear_current_line()
        print(f"  \033[33m⚠\033[0m  {label:<20}  {primary:<16}  → {reason}")
        results.append({
            "name": label,
            "primary": primary,
            "secondary": secondary,
            "ok": False,
        })
        return

    ok, status_code = check_url(target_url)
    clear_current_line()

    tick = "✓" if ok else "✗"
    color_tick = f"\033[32m{tick}\033[0m" if ok else f"\033[31m{tick}\033[0m"
    result_text = f"HTTP {status_code}" if status_code else "Unreachable / Timeout"

    ping = None
    if ok:
        ping = get_ping(primary)
    ping_display = f" (ping: {ping})" if ping else " (ping: N/A)" if ok else ""

    print(f"  {color_tick}  {label:<20}  {primary:<16}  → {result_text}{ping_display}")

    results.append({
        "name": label,
        "primary": primary,
        "secondary": secondary,
        "ok": ok,
        "ping": ping,
    })

# ─────────────────────────────────────────────
# Results Handling
# ─────────────────────────────────────────────
def print_summary(results: List[Dict[str, Any]], total: int) -> None:
    """Print a summary of test results."""
    passed = sum(1 for r in results if r["ok"])
    failed = total - passed
    print(
        f"\n  Result:  "
        f"\033[32m{passed} passed\033[0m  /  "
        f"\033[31m{failed} failed\033[0m  "
        f"out of {total}\n"
    )

def save_working_dns(results: List[Dict[str, Any]]) -> Optional[str]:
    """Save working DNS entries to a timestamped file."""
    working = [r for r in results if r["ok"]]
    if not working:
        return None

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"dns_result_{timestamp}.txt"

    with open(filename, "w", encoding="utf-8") as file:
        file.write("DNS Test Results\n")
        file.write(f"Date & Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        file.write("=" * 60 + "\n\n")
        for r in working:
            secondary = r["secondary"] or ""
            ping = r.get("ping") or "N/A"
            file.write(f"primary: {r['primary']}, secondary: {secondary}, ping: {ping}\n")

    return filename

# ─────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────
def main() -> None:
    """Orchestrate the DNS testing process."""
    enable_ansi()

    if not select_interface():
        return

    target_url = input("\nTarget URL: ").strip()
    if not target_url:
        print("[!] No target URL provided.")
        return

    dns_list = load_dns_list()
    if dns_list is None:
        return

    clear_screen()

    total = len(dns_list)
    print(f"Using interface: {INTERFACE_NAME}")
    print(f"Target URL: {target_url}")
    print(f"DNS entries loaded: {len(dns_list)}")
    print("─" * 56)

    results = []

    try:
        for idx, entry in enumerate(dns_list, 1):
            test_dns_entry(entry, target_url, idx, total, results)
    finally:
        print("\n" + "─" * 56)
        reset_dns_to_auto()
        print("  DNS restored to Automatic (DHCP).")

    print_summary(results, total)

    saved_file = save_working_dns(results)
    if saved_file:
        print(f"\n  ✅ Working DNS saved to '{saved_file}'")
    else:
        print("\n  ❌ No working DNS found.")

if __name__ == "__main__":
    main()