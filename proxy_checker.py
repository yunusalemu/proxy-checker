import os
import json
import requests
import socket
import socks
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ===============================
# 🔑 Load Google API credentials from GitHub Secret
# ===============================
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# ===============================
# 📄 Open your Google Sheet
# ===============================
sheet = client.open("ActiveProxies").sheet1

# ===============================
# 🌍 Get proxy details (geo lookup)
# ===============================
def get_proxy_details(ip):
    try:
        r = requests.get(f"http://ipinfo.io/{ip}/json", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return {
                "country": data.get("country", "Unknown"),
                "region": data.get("region", "Unknown"),
                "city": data.get("city", "Unknown"),
                "org": data.get("org", "Unknown"),
                "isp": data.get("org", "Unknown"),
            }
    except:
        pass
    return {
        "country": "Unknown",
        "region": "Unknown",
        "city": "Unknown",
        "org": "Unknown",
        "isp": "Unknown",
    }

# ===============================
# ✅ Test proxy
# ===============================
def test_proxy(proxy):
    try:
        if len(proxy) == 2:  # ip, port
            ip, port = proxy
            username, password = None, None
        else:  # ip, port, user, pass
            ip, port, username, password = proxy

        socks.set_default_proxy(socks.SOCKS5, ip, int(port), True, username, password)
        socket.socket = socks.socksocket

        # try a simple request
        r = requests.get("http://httpbin.org/ip", timeout=8)
        if r.status_code == 200:
            return True
    except:
        return False
    return False

# ===============================
# 📂 Read proxies.txt
# ===============================
def load_proxies():
    proxies = []
    with open("proxies.txt", "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(":")
            if len(parts) == 2:
                proxies.append((parts[0], parts[1]))
            elif len(parts) == 4:
                proxies.append((parts[0], parts[1], parts[2], parts[3]))
    return proxies

# ===============================
# 📝 Main
# ===============================
def main():
    proxies = load_proxies()
    active_list = []

    for proxy in proxies:
        ip = proxy[0]
        port = proxy[1]
        print(f"Checking {ip}:{port} ...")
        if test_proxy(proxy):
            details = get_proxy_details(ip)
            active_list.append([
                ip, port,
                proxy[2] if len(proxy) > 2 else "",
                proxy[3] if len(proxy) > 3 else "",
                details["country"],
                details["region"],
                details["city"],
                details["isp"],
                details["org"],
                "Yes",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ])

    # Clear and update sheet
    sheet.clear()
    sheet.append_row([
        "Host", "Port", "Username", "Password",
        "Country", "Region", "City", "ISP", "Org",
        "Active", "LastChecked"
    ])
    if active_list:
        sheet.append_rows(active_list)

    print(f"✅ Done. {len(active_list)} active proxies saved to Google Sheet.")

if __name__ == "__main__":
    main()
