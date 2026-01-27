import requests
import yaml
import base64

RAW_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_VLESS_RUS_mobile.txt"

def parse_links(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines

def main():
    raw = requests.get(RAW_URL, timeout=30).text
    links = parse_links(raw)

    proxies = []
    for i, link in enumerate(links):
        proxies.append({
            "name": f"Node-{i+1}",
            "type": "vless",
            "server": "example.com",
            "port": 443,
            "uuid": "00000000-0000-0000-0000-000000000000",
            "tls": True
        })

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
                "proxies": [p["name"] for p in proxies]
            }
        ],
        "rules": [
            "MATCH,AUTO"
        ]
    }

    with open("clash.yaml", "w") as f:
        yaml.dump(clash, f, allow_unicode=True)

if __name__ == "__main__":
    main()
