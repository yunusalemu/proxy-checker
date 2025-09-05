import json
import requests
import socks
import socket
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ============ CONFIG ============
PROXY_SOURCE_FILE = "proxies.txt"   # your pasted proxies file
SHEET_NAME = "ActiveProxies"
# ================================

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

def parse_proxy_line(line):
    """Parse your custom proxy format."""
    parts = line.strip().split("|")
    if len(parts) < 2:
        return None

    ip_parts = parts[0].split(":")
    host = ip_parts[0]
    port = int(ip_parts[1])
    username, password = (None, None)
    if len(ip_parts) == 4:
        username, password = ip_parts[2], ip_parts[3]

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password
    }

def load_proxies():
    """Read proxies from local file."""
    with open(PROXY_SOURCE_FILE, "r") as f:
        lines = f.read().strip().splitlines()
    proxies = []
    for line in lines:
        p = parse_proxy_line(line)
        if p:
            proxies.append(p)
    return proxies

def test_and_get_details(proxy):
    """Check proxy and fetch metadata."""
    try:
        host, port = proxy["host"], proxy["port"]
        user, pwd = proxy.get("username"), proxy.get("password")

        # low-level test
        sock = socks.socksocket()
        if user and pwd:
            sock.set_proxy(socks.SOCKS5, host, port, True, user, pwd)
        else:
            sock.set_proxy(socks.SOCKS5, host, port)
        sock.settimeout(5)
        sock.connect(("httpbin.org", 80))
        sock.close()

        # high-level GeoIP check
        session = requests.Session()
        proxy_auth = f"{user}:{pwd}@" if user else ""
        proxy_url = f"socks5h://{proxy_auth}{host}:{port}"
        session.proxies = {"http": proxy_url, "https": proxy_url}
        r = session.get("http://ip-api.com/json/", timeout=10)

        if r.status_code == 200:
            geo = r.json()
            return {
                "host": host,
                "port": port,
                "username": user or "",
                "password": pwd or "",
                "country": geo.get("country"),
                "region": geo.get("regionName"),
                "city": geo.get("city"),
                "isp": geo.get("isp"),
                "org": geo.get("org"),
                "active": "Yes",
                "last_checked": datetime.utcnow().isoformat()
            }
    except Exception:
        pass
    return None

def update_google_sheet(proxies):
    """Save active proxies to Google Sheets with newest on top."""
    # clear old sheet (but keep headers)
    existing = sheet.get_all_records()
    if existing:
        sheet.delete_rows(2, len(existing)+1)

    rows = []
    for p in proxies:
        rows.append([
            p["host"],
            p["port"],
            p["username"],
            p["password"],
            p["country"],
            p["region"],
            p["city"],
            p["isp"],
            p["org"],
            p["active"],
            p["last_checked"]
        ])

    # insert new rows at top (after header)
    if rows:
        sheet.insert_rows(rows, 2)

def main():
    raw_proxies = load_proxies()
    active = []
    for proxy in raw_proxies:
        info = test_and_get_details(proxy)
        if info:
            active.append(info)
    print(f"[INFO] Active proxies: {len(active)}")
    if active:
        update_google_sheet(active)

if __name__ == "__main__":
    main()
