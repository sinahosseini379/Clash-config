import requests
import yaml
import base64
import json
from urllib.parse import urlparse, parse_qs
import concurrent.futures
import time
import socket

RAW_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_VLESS_RUS_mobile.txt"
PRIORITY_LOCATIONS = ["US", "DE", "FI"]
TIMEOUT = 3  # ثانیه برای تست نود


def parse_vmess(link):
    data = link.replace("vmess://", "")
    decoded = base64.b64decode(data + "===").decode()
    obj = json.loads(decoded)
    return {
        "name": obj.get("ps", "vmess"),
        "type": "vmess",
        "server": obj.get("add"),
        "port": int(obj.get("port")),
        "uuid": obj.get("id"),
        "alterId": int(obj.get("aid", 0)),
        "cipher": "auto",
        "tls": obj.get("tls") == "tls",
        "network": obj.get("net"),
        "ws-opts": {
            "path": obj.get("path", "/"),
            "headers": {"Host": obj.get("host", "")}
        } if obj.get("net") == "ws" else None,
        "location": obj.get("country", "unknown"),
        "tunnel_mode": True
    }


def parse_vless(link):
    u = urlparse(link.replace("vless://", "http://"))
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
        "servername": q.get("sni", [None])[0],
        "location": q.get("loc", ["unknown"])[0],
        "tunnel_mode": True
    }


def test_latency(node):
    try:
        start = time.time()
        s = socket.create_connection((node['server'], node['port']), timeout=TIMEOUT)
        s.close()
        return time.time() - start
    except Exception:
        return TIMEOUT + 1  # تایم‌اوت میره آخر لیست


def rank_nodes(nodes):
    # تست latency همزمان
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(test_latency, nodes))

    for node, latency in zip(nodes, results):
        node['latency'] = latency

    # مرتب سازی: ابتدا بر اساس لوکیشن، سپس latency
    def key_fn(n):
        loc_index = PRIORITY_LOCATIONS.index(n['location']) if n['location'] in PRIORITY_LOCATIONS else len(PRIORITY_LOCATIONS)
        return (loc_index, n['latency'])

    nodes.sort(key=key_fn)
    return nodes


def main():
    raw = requests.get(RAW_URL, timeout=30).text
    lines = [l.strip() for l in raw.splitlines() if l.strip()]

    proxies = []

    for l in lines:
        try:
            if l.startswith("vmess://"):
                proxies.append(parse_vmess(l))
            elif l.startswith("vless://"):
                proxies.append(parse_vless(l))
        except Exception as e:
            print("Parse error:", e)

    proxies = rank_nodes(proxies)

    proxy_names = [p["name"] for p in proxies]

    clash = {
        "mixed-port": 7890,
        "allow-lan": True,
        "mode": "rule",
        "log-level": "info",
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "AUTO",
                "type": "url-test",
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "proxies": proxy_names
            },
            {
                "name": "BACKUP",
                "type": "fallback",
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "proxies": proxy_names
            }
        ],
        "rules": [
            "DOMAIN-SUFFIX,google.com,AUTO",
            "DOMAIN-SUFFIX,youtube.com,AUTO",
            "MATCH,BACKUP"
        ]
    }

    singbox_config = {
        "inbounds": [],
        "outbounds": proxies
    }

    with open("clash.yaml", "w", encoding="utf-8") as f:
        yaml.dump(clash, f, allow_unicode=True)

    with open("singbox.json", "w", encoding="utf-8") as f:
        json.dump(singbox_config, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
