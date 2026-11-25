#!/usr/bin/env python3
"""Safely inspect and probe the BIP dynamic list API without logging credentials."""
import json
import re
import urllib.request
import urllib.parse
from html.parser import HTMLParser

URLS = [
    ("Interpelacje", "https://bip.gdansk.pl/rada-miasta/publikacja-interpelacji-radnych-miasta-gdanska", "publikacja-interpelacji-radnych-miasta-gdanska"),
    ("Zapytania radnych", "https://bip.gdansk.pl/rada-miasta/publikacja-zapytan-radnych-miasta-gdanska", "publikacja-zapytan-radnych-miasta-gdanska"),
    ("Petycje", "https://bip.gdansk.pl/urzad-miejski/publikacja-petycji-do-rady-miasta-gdanska", "publikacja-petycji-do-rady-miasta-gdanska"),
]
HEADERS = {"User-Agent": "GdanskRadar/0.1 (public-source monitor; contact: racibo.pl)"}

class ScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.scripts.append(dict(attrs))

def get_bytes(url, headers=None):
    req = urllib.request.Request(url, headers={**HEADERS, **(headers or {})})
    with urllib.request.urlopen(req, timeout=35) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read()

def get_text(url):
    return get_bytes(url)[2].decode("utf-8", "replace")

for label, page_url, endpoint in URLS:
    print("\\n=== ", label, "===")
    try:
        page = get_text(page_url)
        parser = ScriptParser()
        parser.feed(page)
        endpoint_script = None
        for attrs in parser.scripts:
            src = attrs.get("src", "")
            if endpoint in src:
                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    src = "https://bip.gdansk.pl" + src
                elif not src.startswith("http"):
                    src = page_url.rsplit("/", 1)[0] + "/" + src
                endpoint_script = get_text(src)
                break
        if not endpoint_script:
            print("Endpoint script not found")
            continue
        auth = re.search(r'Authorization\s*:\s*["\']([^"\']+)["\']', endpoint_script)
        if not auth:
            print("Authorization constant not found")
            continue
        api_url = "https://bip.gdansk.pl/picklock/" + endpoint + "?" + urllib.parse.urlencode({
            "rok": "2026",
            "wyszukiwana_tresc": ""
        })
        status, content_type, body = get_bytes(api_url, {
            "Authorization": auth.group(1),
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Referer": page_url,
        })
        text = body.decode("utf-8", "replace")
        print("API HTTP:", status, "| type:", content_type, "| bytes:", len(body))
        try:
            data = json.loads(text)
            results = data.get("results", "")
            print("JSON keys:", sorted(data.keys()))
            print("API status field:", data.get("status"))
            print("Results type:", type(results).__name__, "| chars:", len(results) if isinstance(results, str) else "n/a")
            if isinstance(results, str):
                print("CRZ markers:", len(re.findall(r"CRZ\\s*[:|]?\\s*\\d{1,3}/\\d{2,4}", results, re.I)))
                print("Numer markers:", len(re.findall(r"Numer\\s+\\d{1,3}/\\d{4}", results, re.I)))
                sample = re.sub(r"\\s+", " ", results[:2600])
                print("HTML prefix sample:", sample[:1800])
                class TextProbe(HTMLParser):
                    def __init__(self): super().__init__(); self.parts=[]
                    def handle_data(self, value):
                        value=value.strip()
                        if value: self.parts.append(value)
                probe=TextProbe(); probe.feed(results)
                print("Visible text sample:", " | ".join(probe.parts)[:1800])
        except Exception:
            print("Response is not JSON; prefix:", re.sub(r"\\s+", " ", text[:240]))
    except Exception as exc:
        print("PROBE ERROR:", type(exc).__name__, str(exc)[:300])
