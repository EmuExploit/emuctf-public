import html
import subprocess
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ping Utility</title>
  <style>
    :root { color-scheme: dark; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #0b1020; color: #e8edf7; }
    main { width: min(720px, calc(100% - 32px)); padding: 32px; background: #151c31; border: 1px solid #2a3658; border-radius: 14px; box-shadow: 0 24px 80px #0008; }
    h1 { margin: 0 0 8px; font-size: 1.6rem; }
    p { margin: 0 0 24px; color: #aeb9d2; }
    form { display: flex; gap: 10px; }
    input { flex: 1; min-width: 0; padding: 12px 14px; border: 1px solid #3b496d; border-radius: 8px; background: #0b1020; color: inherit; font: inherit; }
    button { padding: 12px 20px; border: 0; border-radius: 8px; background: #63d4a7; color: #07120e; font: inherit; font-weight: 700; cursor: pointer; }
    pre { min-height: 96px; margin: 24px 0 0; padding: 16px; overflow: auto; white-space: pre-wrap; background: #080c17; border-radius: 8px; color: #c7d2ea; }
    @media (max-width: 520px) { form { flex-direction: column; } }
  </style>
</head>
<body>
  <main>
    <h1>Ping Utility</h1>
    <p>Check whether an IP address responds.</p>
    <form method="get">
      <input name="ip" value="__IP__" placeholder="127.0.0.1" aria-label="IP address" autofocus required>
      <button type="submit">Ping</button>
    </form>
    <pre>__OUTPUT__</pre>
  </main>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        ip = query.get("ip", [""])[0]
        output = "Enter an IP address to begin."
        if ip:
            try:
                result = subprocess.run(
                    "busybox ping -c 1 " + ip,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=4,
                )
                output = result.stdout + result.stderr
            except subprocess.TimeoutExpired:
                output = "Ping timed out."
        body = PAGE.replace("__IP__", html.escape(ip)).replace("__OUTPUT__", html.escape(output)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
