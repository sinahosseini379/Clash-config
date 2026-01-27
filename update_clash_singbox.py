import yaml
import json
import requests

# لینک VLESS واقعی
VLESS_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_VLESS_RUS_mobile.txt"

# اولویت کشورها
COUNTRY_PRIORITY = ["US", "DE", "FI", "RU", "IR"]

def fetch_vless_nodes(url):
    res = requests.get(url)
    res.raise_for_status()
    lines = res.text.splitlines()
    nodes = []
    for line in lines:
        line = line.strip()
        if line.startswith("vless://") or line.startswith("vmess://"):
            nodes.append(line)
    return nodes

def parse_vless(line):
    # parse واقعی VLESS
    import base64, urllib.parse
    if line.startswith("vless://"):
        # vless://UUID@server:port?params#name
        import re
        match = re.match(r"vless://([0-9a-fA-F-]+)@([\w\.\-]+):(\d+)\?([^\#]+)\#?(.*)", line)
        if not match:
            return None
        uuid, server, port, query, name = match.groups()
        params = dict(urllib.parse.parse_qsl(query))
        node = {
            "name": name or server,
            "type": "vless",
            "server": server,
            "port": int(port),
            "uuid": uuid,
            "tls": params.get("security", "none") == "tls",
            "flow": params.get("flow"),
            "network": params.get("type", "tcp"),
            "servername": params.get("host", server),
        }
        return node
    return None

def generate_clash_yaml(nodes):
    clash_conf = {
        "allow-lan": True,
        "log-level": "info",
        "mode": "rule",
        "mixed-port": 7890,
        "proxies": nodes
    }
    with open("clash.yaml", "w") as f:
        yaml.dump(clash_conf, f, sort_keys=False)

def generate_singbox_json(nodes):
    singbox_conf = {
        "outbounds": nodes
    }
    with open("singbox.json", "w") as f:
        json.dump(singbox_conf, f, indent=2)

def main():
    lines = fetch_vless_nodes(VLESS_URL)
    nodes = [parse_vless(l) for l in lines if parse_vless(l)]
    
    # اولویت‌بندی کشور
    nodes_sorted = sorted(nodes, key=lambda n: next((i for i, c in enumerate(COUNTRY_PRIORITY) if c in n["server"]), len(COUNTRY_PRIORITY)))
    
    generate_clash_yaml(nodes_sorted)
    generate_singbox_json(nodes_sorted)
    print(f"Generated {len(nodes_sorted)} nodes for Clash & Sing-box.")

if __name__ == "__main__":
    main()
