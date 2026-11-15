const express = require('express');
const axios = require('axios');

const HOST = '0.0.0.0';
const PORT = Number(process.env.PORT || 8080);
const API_KEY = process.env.INTERNAL_API_KEY || 'placeholder_internal_api_key';
const INTERNAL_API = process.env.INTERNAL_API_URL || 'http://127.0.0.1:3000';

const api = axios.create({
  baseURL: INTERNAL_API,
  timeout: 5000,
  headers: { Authorization: `Bearer ${API_KEY}` },
  validateStatus: () => true,
  maxRedirects: 0,
  maxContentLength: 1_000_000,
  maxBodyLength: 1_000_000,
});

const app = express();
app.disable('x-powered-by');
app.disable('etag');

app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader(
    'Content-Security-Policy',
    "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
  );
  next();
});

function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const money = (n) => '$' + Number(n || 0).toLocaleString('en-AU');

function layout(title, body) {
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${esc(title)}</title>
  <style>
    :root { color-scheme: dark; --paper:#1a1410; --ink:#f3e7d3; --accent:#d8a657; --danger:#e06c5e; --line:#4a3a28; font-family: "Courier New", ui-monospace, monospace; }
    * { box-sizing: border-box; }
    body { margin:0; min-height:100vh; background:
        radial-gradient(1200px 600px at 50% -10%, #2a2015 0%, #120d09 70%), var(--paper);
      color:var(--ink); padding:32px 16px 64px; }
    a { color:var(--accent); }
    header.masthead { max-width:1040px; margin:0 auto 28px; text-align:center; border-bottom:3px double var(--line); padding-bottom:18px; }
    header.masthead .ribbon { letter-spacing:.5em; color:var(--danger); font-size:.75rem; text-transform:uppercase; }
    header.masthead h1 { margin:6px 0 2px; font-size:clamp(2rem,6vw,3.4rem); letter-spacing:.08em; text-shadow:2px 2px 0 #000; }
    header.masthead p { margin:4px 0 0; color:#b9a888; font-size:.85rem; }
    main { max-width:1040px; margin:0 auto; }
    .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:18px; }
    .card { background:var(--paper); border:2px solid var(--line); border-radius:6px; padding:18px; box-shadow:4px 4px 0 #0007; display:flex; flex-direction:column; }
    .card h2 { margin:0 0 2px; font-size:1.25rem; }
    .mug { height:140px; margin-bottom:14px; border:1px solid var(--line); border-radius:4px; display:grid; place-items:center; overflow:hidden; background:
        repeating-linear-gradient(45deg,#241a11,#241a11 14px,#1c140d 14px,#1c140d 28px); font-size:3.4rem; }
    .mug img { display:block; height:100%; max-width:100%; object-fit:contain; font-size:.7rem; }
    .status { display:inline-block; color:var(--danger); border:1px solid var(--danger); border-radius:3px; padding:2px 8px; font-size:.72rem; letter-spacing:.1em; margin-bottom:10px; }
    .prize { font-size:1.6rem; color:var(--accent); font-weight:bold; margin:auto 0 0; }
    .prize small { display:block; color:#b9a888; font-size:.65rem; letter-spacing:.2em; font-weight:normal; }
    .btn { margin-top:14px; text-align:center; text-decoration:none; border:1px solid var(--accent); color:var(--accent); padding:8px; border-radius:4px; }
    .btn:hover { background:var(--accent); color:#120d09; }
    .dossier { background:var(--paper); border:2px solid var(--line); border-radius:6px; padding:28px; box-shadow:6px 6px 0 #0008; }
    .dossier .mug { height:200px; font-size:5rem; max-width:220px; }
    .dossier dl { display:grid; grid-template-columns:160px 1fr; gap:10px 18px; margin:22px 0 0; }
    .dossier dt { color:var(--accent); letter-spacing:.08em; text-transform:uppercase; font-size:.75rem; padding-top:3px; }
    .dossier dd { margin:0; }
    .back { display:inline-block; margin-bottom:18px; }
    .err { max-width:620px; margin:40px auto; text-align:center; border:2px dashed var(--danger); padding:28px; color:var(--danger); }
    footer { max-width:1040px; margin:40px auto 0; text-align:center; color:#6e5c44; font-size:.7rem; border-top:1px solid var(--line); padding-top:14px; }
  </style>
</head>
<body>
  <header class="masthead">
    <div class="ribbon">By order of the Department of Avian Affairs</div>
    <h1>EMU MOST WANTED</h1>
    <p>Western Australia's registry of feathered fugitives &mdash; report sightings to your nearest ranger</p>
  </header>
  <main>${body}</main>
  <footer>Emu Most Wanted &middot; Public bulletin. Apprehension of listed emus is subject to local wildlife statutes.</footer>
</body>
</html>`;
}

function renderMug(e) {
  const file = e.mugshot || 'default.jpg';
  return `<div class="mug"><img src="/mugshot/${encodeURIComponent(file)}" alt="Mugshot of ${esc(e.name)}"></div>`;
}

function renderList(emus) {
  if (!emus.length) {
    return `<div class="err">No emus are currently on file. Western Australia is (briefly) safe.</div>`;
  }
  const cards = emus
    .map(
      (e) => `
      <article class="card">
        ${renderMug(e)}
        <span class="status">${esc(e.status)}</span>
        <h2>${esc(e.name)}</h2>
        <div class="prize">${esc(money(e.prize))}<small>Reward &middot; Danger: ${esc(e.danger)}</small></div>
        <a class="btn" href="/emu/${encodeURIComponent(e.id)}">View rap sheet &rarr;</a>
      </article>`
    )
    .join('');
  return `<div class="grid">${cards}</div>`;
}

function renderDetail(e) {
  return `
    <a class="back" href="/">&larr; Back to the registry</a>
    <article class="dossier">
      ${renderMug(e)}
      <span class="status">${esc(e.status)}</span>
      <h2>${esc(e.name)}</h2>
      <dl>
        <dt>Reward</dt><dd>${esc(money(e.prize))} for capture dead or alive</dd>
        <dt>Danger level</dt><dd>${esc(e.danger)}</dd>
        <dt>Known crimes</dt><dd>${esc(e.crimes)}</dd>
        <dt>Last seen</dt><dd>${esc(e.last_seen)}</dd>
        <dt>Ranger notes</dt><dd>${esc(e.notes)}</dd>
      </dl>
    </article>`;
}

function renderError(message) {
  return `<div class="err">${esc(message)}</div>`;
}

app.get('/', async (req, res) => {
  try {
    const resp = await api.get('/api/emus');
    if (resp.status !== 200 || !resp.data || !Array.isArray(resp.data.emus)) {
      throw new Error(`unexpected api response (${resp.status})`);
    }
    res.send(layout('Emu Most Wanted', renderList(resp.data.emus)));
  } catch (err) {
    res
      .status(502)
      .send(layout('Registry offline', renderError('The registry is temporarily unavailable.')));
  }
});

app.get('/emu/:id', async (req, res) => {
  const id = req.params.id;

  let resp;
  try {
    resp = await api.get(`/api/emus/${id}`);
    if (resp.status === 404) {
      return res.status(404).send(layout('Not found', renderError('No such emu on file.')));
    }
    if (resp.status !== 200) {
      throw new Error(`unexpected api response (${resp.status})`);
    }
  } catch (err) {
    console.log(err);
    res
      .status(502)
      .send(layout('Registry offline', renderError('The registry is temporarily unavailable.')));
  }

  try {
    const emu = resp.data.emu;
    res.send(layout(`${emu.name} — Emu Most Wanted`, renderDetail(emu)));
  } catch (err) {
    console.log(err);
    res
      .status(502)
      .send(layout('Invalid Response', renderError(`Invalid response body was received: ${JSON.stringify(resp.data)}`)));
  }
});

app.get('/mugshot/:file', async (req, res) => {
  const file = req.params.file;

  try {
    const resp = await api.get(`/api/mugshots/${file}`, { responseType: 'arraybuffer' });
    if (resp.status === 404) {
      return res.status(404).send(layout('Not found', renderError('No such mugshot on file.')));
    }
    if (resp.status !== 200) {
      throw new Error(`unexpected api response (${resp.status})`);
    }
    res.setHeader('Cache-Control', 'public, max-age=3600');
    res.type(resp.headers['content-type'] || 'application/octet-stream');
    res.send(Buffer.from(resp.data));
  } catch (err) {
    console.log(err);
    res
      .status(502)
      .send(layout('Registry offline', renderError('The registry is temporarily unavailable.')));
  }
});

app.use((req, res) => {
  res.status(404).send(layout('Not found', renderError('Page not found.')));
});

app.listen(PORT, HOST, () => {
  console.log(`[external] Emu Most Wanted listening on http://${HOST}:${PORT}`);
});
