import re
import sys
from collections import defaultdict
from html.parser import HTMLParser

BACKSPACE, LEFT = 8, 37


class SpanParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.color = None
        self.chars = []  # (hex color, char)

    def handle_starttag(self, tag, attrs):
        if tag == "span":
            style = dict(attrs).get("style", "")
            m = re.search(r"(?<!-)color:\s*#([0-9A-Fa-f]{6})", style)
            self.color = m.group(1).upper() if m else None

    def handle_endtag(self, tag):
        if tag == "span":
            self.color = None

    def handle_data(self, data):
        for ch in data:
            if not ch.isspace():
                self.chars.append((self.color, ch))


def load_keys(csv_path):
    """Key-down VKs in chronological order (log is newest-first, UTF-16)."""
    with open(csv_path, encoding="utf-16") as f:
        rows = f.read().splitlines()[1:]
    keys = []
    for r in reversed(rows):
        ev = r.split(";")[3]
        if ev.startswith("D("):
            keys.append(int(ev.split("VK=")[1].split(",")[0]))
    return keys


def apply(arr, keys):
    arr, cur = list(arr), len(arr)  # cursor starts at end
    for vk in keys:
        if vk == LEFT:
            cur = max(0, cur - 1)
        elif vk == BACKSPACE and cur > 0:
            del arr[cur - 1]
            cur -= 1
    return arr


if __name__ == "__main__":
    html = sys.argv[1] if len(sys.argv) > 1 else "buffer.html"
    csv = sys.argv[2] if len(sys.argv) > 2 else "input.csv"
    p = SpanParser()
    with open(html, encoding="utf-8") as f:
        p.feed(f.read())
    out = apply(p.chars, load_keys(csv))

    streams = defaultdict(str)
    for col, ch in out:
        streams[col] += ch

    for col, stream in streams.items():
        print(f"{col}: {stream}")
