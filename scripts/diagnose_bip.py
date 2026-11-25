#!/usr/bin/env python3
"""Safely inspect BIP dynamic list configuration without logging credentials."""
import re
import urllib.request
from html.parser import HTMLParser

URLS = [
    "https://bip.gdansk.pl/rada-miasta/publikacja-interpelacji-radnych-miasta-gdanska",
    "https://bip.gdansk.pl/rada-miasta/publikacja-zapytan-radnych-miasta-gdanska",
    "https://bip.gdansk.pl/urzad-miejski/publikacja-petycji-do-rady-miasta-gdanska",
]
HEADERS = {"User-Agent": "GdanskRadar/0.1 (public-source monitor; contact: racibo.pl)"}
BASE = re.compile(r"urlPicklock", re.I)
ASSIGNMENT = re.compile(r"""(?:urlPicklock|picklockUrl)\s*[:=]\s*["']([^"']+)["']""", re.I)
AUTH = re.compile(r'Authorization\s*:\s*["\'][^"\']+["\']', re.I)

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

def safe_snippets(label, source):
    hits = list(BASE.finditer(source))
    print(label, "urlPicklock occurrences:", len(hits))
    for match in hits[:8]:
        start, end = max(0, match.start()-180), min(len(source), match.end()+260)
        snippet = re.sub(r"\\s+", " ", source[start:end])
        snippet = AUTH.sub('Authorization:"[REDACTED]"', snippet)
        print("  CONFIG:", snippet[:520])
    for value in ASSIGNMENT.findall(source):
        print("  BASE URL:", value)

for page_url in URLS:
    print("\\n=== PAGE:", page_url, "===")
    try:
        html = get(page_url)
    except Exception as exc:
        print("PAGE ERROR:", repr(exc))
        continue
    print("HTML bytes:", len(html))
    safe_snippets("HTML", html)
    parser = ScriptParser()
    parser.feed(html)
    print("Scripts:", len(parser.scripts))
    for script in parser.scripts:
        src = script["src"]
        if not src:
            if script["inline"].strip():
                safe_snippets("INLINE", script["inline"])
            continue
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = "https://bip.gdansk.pl" + src
        elif not src.startswith("http"):
            src = page_url.rsplit("/", 1)[0] + "/" + src
        try:
            js = get(src)
            if BASE.search(js):
                print("SCRIPT:", src, "| bytes:", len(js))
                safe_snippets("SCRIPT", js)
        except Exception as exc:
            print("SCRIPT ERROR:", src, repr(exc))
