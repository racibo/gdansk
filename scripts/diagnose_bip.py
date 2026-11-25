#!/usr/bin/env python3
"""Inspect BIP page script assets to discover where council lists are loaded."""
import re
import urllib.request
from html.parser import HTMLParser

URLS = [
    "https://bip.gdansk.pl/rada-miasta/publikacja-interpelacji-radnych-miasta-gdanska",
    "https://bip.gdansk.pl/rada-miasta/publikacja-zapytan-radnych-miasta-gdanska",
    "https://bip.gdansk.pl/urzad-miejski/publikacja-petycji-do-rady-miasta-gdanska",
]
HEADERS = {"User-Agent": "GdanskRadar/0.1 (public-source monitor; contact: racibo.pl)"}
KEYWORDS = re.compile(r"ajax|api|json|crz|interpel|zapyt|petycj|graphql|fetch\\s*\\(", re.I)

class ScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.current = None
    def handle_starttag(self, tag, attrs):
        if tag == "script":
            attrs = dict(attrs)
            self.current = {"src": attrs.get("src", ""), "inline": ""}
            self.scripts.append(self.current)
    def handle_data(self, data):
        if self.current is not None:
            self.current["inline"] += data
    def handle_endtag(self, tag):
        if tag == "script":
            self.current = None

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", "replace")

for page_url in URLS:
    print("\\n=== PAGE:", page_url, "===")
    try:
        html = get(page_url)
    except Exception as exc:
        print("PAGE ERROR:", repr(exc))
        continue
    parser = ScriptParser()
    parser.feed(html)
    print("HTML bytes:", len(html), "| scripts:", len(parser.scripts))
    for script in parser.scripts:
        src = script["src"]
        if src:
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = "https://bip.gdansk.pl" + src
            elif not src.startswith("http"):
                src = page_url.rsplit("/", 1)[0] + "/" + src
            print("SCRIPT:", src)
            try:
                js = get(src)
                print("  JS bytes:", len(js))
                hits = 0
                for match in KEYWORDS.finditer(js):
                    start = max(0, match.start() - 140)
                    end = min(len(js), match.end() + 240)
                    snippet = re.sub(r"\\s+", " ", js[start:end])
                    print("  MATCH:", snippet[:420])
                    hits += 1
                    if hits >= 12:
                        print("  ... match limit reached")
                        break
            except Exception as exc:
                print("  SCRIPT ERROR:", repr(exc))
        elif script["inline"].strip():
            inline = script["inline"]
            print("INLINE script chars:", len(inline))
            for match in KEYWORDS.finditer(inline):
                print("  INLINE MATCH:", re.sub(r"\\s+", " ", inline[max(0,match.start()-100):match.end()+180])[:360])
