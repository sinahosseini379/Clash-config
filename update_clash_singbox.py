#!/usr/bin/env python3
import yaml
import json
import requests
from urllib.parse import urlparse, parse_qs

CONFIG_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_VLESS_RUS_mobile.txt"
PREFERRED_COUNTRIES = ["US", "DE", "FI", "AT", "SE", "NL", "CH"]

def fetch_nodes(url):
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    lines = r.text.splitlines()
    nodes = []
    for line in lines:
        line = line.strip()
        if line.startswith("vless://") or line.startswith("vmess://"):
            nodes.append(line)
    return nodes

def parse_vless(url):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    node = {
        "name": parsed.fragment if parsed.fragment else parsed.hostname,
        "type": "vless",
        "server": parsed.hostname,
        "port": int(parsed.port),
        "uuid": parsed.username,
        "tls": params.get("security", ["none"])[0].lower() == "tls",
        "network": params.get("type", ["tcp"])[0],
        "flow": params.get("flow", [None])[0],
        "servername": params.get("sni", [parsed.hostname])[0],
    }
    if node["network"] == "ws":
        node["ws-opts"] = {
            "path": params.get("path", ["/"])[0],
            "headers": {"Host": params.get("host", [parsed.hostname])[0]},
        }
    return node

def sort_nodes(nodes):
    def get_priority(name):
        for i, country in enumerate(PREFERRED_COUNTRIES):
            if country.lower() in name.lower():
                return i
        return len(PREFERRED_COUNTRIES)
    return sorted(nodes, key=lambda n: get_priority(n["name"]))

def build_clash_yaml(nodes):
    proxies = nodes
    proxy_names = [n["name"] for n in nodes]
    clash_config = {
        "allow-lan": True,
        "log-level": "info",
        "mode": "rule",
        "mixed-port": 7890,
        "proxies": proxies,
        "proxy-groups": [
            {"name": "AUTO", "type": "fallback", "proxies": proxy_names, "url": "http://www.gstatic.com/generate_204", "interval": 300},
            {"name": "BACKUP", "type": "select", "proxies": proxy_names},
            {"name": "🇮🇷 Iran", "type": "select", "proxies": proxy_names}
        ],
        "rules": ["MATCH,AUTO"]
    }
    return clash_config

def build_singbox_json(nodes):
    outbounds = []
    for n in nodes:
        outbound = {
            "type": n["type"],
            "tag": n["name"],
            "server": n["server"],
            "port": n["port"],
            "uuid": n["uuid"],
            "tls": n["tls"],
            "network": n.get("network", "tcp"),
            "flow": n.get("flow", None),
            "ws-opts": n.get("ws-opts", None)
        }
        outbounds.append(outbound)
    return {"outbounds": outbounds}

def main():
    raw_nodes = fetch_nodes(CONFIG_URL)
    parsed_nodes = []
    for url in raw_nodes:
        if url.startswith("vless://"):
            parsed_nodes.append(parse_vless(url))
    sorted_nodes = sort_nodes(parsed_nodes)
    clash_config = build_clash_yaml(sorted_nodes)
    with open("clash.yaml", "w") as f:
        yaml.dump(clash_config, f, allow_unicode=True)
    singbox_config = build_singbox_json(sorted_nodes)
    with open("singbox.json", "w") as f:
        json.dump(singbox_config, f, indent=2)
    print("✅ Clash & Sing-box configs updated successfully.")

if __name__ == "__main__":
    main()
