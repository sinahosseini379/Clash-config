import requests
import yaml
import json
import re
import base64
from urllib.parse import urlparse, parse_qs

# -------------------------------
# تنظیمات اولیه
# -------------------------------
RAW_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_VLESS_RUS_mobile.txt"

# ترتیب اولویت لوکیشن‌ها (می‌تونی تغییر بدی)
PRIORITY_ORDER = ["US", "DE", "FI", "RU", "AT", "FR", "JP"]

# -------------------------------
# توابع استخراج لینک‌ها
# -------------------------------
def extract_links(text):
    """
    پیدا کردن تمام لینک‌های VLESS و Vmess در متن
    """
    pattern = r"(vless://[^\s]+|vmess://[A-Za-z0-9+/=]+)"
    return re.findall(pattern, text)

# -------------------------------
# توابع parse
# -------------------------------
def parse_vmess(link):
    """
    تبدیل لینک vmess:// به دیکشنری مناسب Clash/Sing-box
    """
    b64 = link.replace("vmess://", "")
    # padding base64
    b64 += "=" * ((4 - len(b64) % 4) % 4)
    decoded = json.loads(base64.b64decode(b64).decode())
    return {
        "name": decoded.get("ps", "vmess"),
        "type": "vmess",
        "server": decoded.get("add"),
        "port": int(decoded.get("port", 0)),
        "uuid": decoded.get("id", ""),
        "cipher": "auto",
        "tls": decoded.get("tls") == "tls",
        "network": decoded.get("net", "tcp"),
        "ws-opts": {
            "path": decoded.get("path", "/"),
            "headers": {"Host": decoded.get("host", "")}
        } if decoded.get("net") == "ws" else None
    }

def parse_vless(link):
    """
    تبدیل لینک vless:// به دیکشنری مناسب Clash/Sing-box
    """
    # urlparse نیاز به scheme داره
    link_fixed = link.replace("vless://", "http://")
    u = urlparse(link_fixed)
    q = parse_qs(u.query)
    return {
        "name": u.hostname,
        "type": "vless",
        "server": u.hostname,
        "port": u.port,
        "uuid": u.username,
        "tls": q.get("security", [""])[0] == "tls",
        "flow": q.get("flow", [None])[0],
        "network": q.get("type", ["tcp"])[0],
        "servername": q.get("sni", [None])[0]
    }

# -------------------------------
# مرتب‌سازی بر اساس لوکیشن
# -------------------------------
def sort_by_location(proxies):
    def get_priority(proxy):
        for i, code in enumerate(PRIORITY_ORDER):
            if code.lower() in proxy.get("server", "").lower():
                return i
        return len(PRIORITY_ORDER)
    return sorted(proxies, key=get_priority)

# -------------------------------
# main
# -------------------------------
def main():
    print("Downloading subscription...")
    text = requests.get(RAW_URL, timeout=15).text
    links = extract_links(text)

    print(f"Found {len(links)} links")
    proxies = []

    for link in links:
        try:
            if link.startswith("vmess://"):
                proxies.append(parse_vmess(link))
            elif link.startswith("vless://"):
                proxies.append(parse_vless(link))
        except Exception as e:
            print(f"Error parsing link: {link} -> {e}")

    # مرتب‌سازی نودها بر اساس لوکیشن
    proxies = sort_by_location(proxies)

    # ساخت YAML خروجی Clash
    clash = {
        "allow-lan": True,
        "log-level": "info",
        "mode": "rule",
        "mixed-port": 7890,
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "AUTO",
                "type": "url-test",
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "proxies": [p["name"] for p in proxies]
            }
        ],
        "rules": ["MATCH,AUTO"]
    }

    with open("clash.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(clash, f, sort_keys=False)

    # ساخت خروجی sing-box
    singbox_config = {"outbounds": proxies, "inbounds": []}
    with open("singbox.json", "w", encoding="utf-8") as f:
        json.dump(singbox_config, f, indent=2)

    print("Clash & Sing-box configs generated successfully!")

if __name__ == "__main__":
    main()
