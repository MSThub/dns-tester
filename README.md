# DNS Checker

A simple Windows utility for testing multiple DNS servers against a target website.

The tool automatically:

* Changes the system DNS
* Verifies that the DNS was applied correctly
* Tests DNS resolution using `nslookup`
* Checks accessibility of a target URL
* Measures DNS server ping (when available)
* Restores DNS settings to DHCP after completion
* Saves working DNS servers to a result file

---

📖 **Looking for the Persian (فارسی) documentation?**

Read the Persian version here: **[README_fa.md](README_fa.md)**

---

## A little preview 
<img width="649" height="688" alt="image" src="https://github.com/user-attachments/assets/1f9be5bf-103e-40db-80d7-aba0471d0206" />

*The tool tests multiple DNS servers against a target URL. Each result shows the DNS name, IP address, HTTP status, and ping response time (if successful). At the end, a summary and the saved result file are displayed.*

---

## Requirements

* Windows
* Python 3.10+
* Administrator privileges

Install dependencies:

```bash
pip install requests
```

---

## Files

| File               | Description                                       |
| ------------------ | ------------------------------------------------- |
| `dns-checker.py`   | Main application                                  |
| `start.bat`        | Launches the script with Administrator privileges |
| `dns_list.txt`     | DNS server list                                   |
| `dns_result_*.txt` | Generated result file with working DNS servers    |

---

## DNS List Format

Edit `dns_list.txt` and add DNS servers using this format:

```text
primary,secondary,name
```

Examples:

```text
1.1.1.1,1.0.0.1,Cloudflare
8.8.8.8,8.8.4.4,Google
9.9.9.9,,Quad9
94.140.14.14
```

### Notes

* `secondary` is optional
* `name` is optional
* Empty lines are ignored
* Lines starting with `#` are treated as comments

---

## Usage

### Option 1 (Recommended)

Run:

```text
start.bat
```

The batch file automatically requests Administrator privileges if needed.

### Option 2

Run the script manually from an Administrator terminal:

```bash
python dns-checker.py
```

---

## Example

```text
Available Network Interfaces:

1. Ethernet
2. Wi-Fi

Select interface: 2

Target URL: auth.ea.com

[1/5] Testing Cloudflare...
✓ Cloudflare → HTTP 200 (ping: 24ms)

[2/5] Testing Google...
✓ Google → HTTP 200 (ping: 31ms)

[3/5] Testing Quad9...
⚠ DNS not responding
```

---

## Output

After testing is completed, all working DNS servers are saved to a timestamped file:

```text
dns_result_2026-06-23_15-30-22.txt
```

Example:

```text
primary: 1.1.1.1, secondary: 1.0.0.1, ping: 24ms
primary: 8.8.8.8, secondary: 8.8.4.4, ping: 31ms
```

---

## Disclaimer

This tool modifies the DNS settings of the selected network interface during testing.

DNS settings are automatically restored to DHCP after execution, even if the test process is interrupted.
