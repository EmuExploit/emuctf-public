"use strict";

const fs = require("fs");
const path = require("path");
const express = require("express");
const puppeteer = require("puppeteer-core");

const CONFIG = {
  port: parseInt(process.env.PORT || "8080", 10),
  chromiumPath: process.env.CHROMIUM_PATH || "/usr/bin/chromium",
  visitTimeoutMs: parseInt(process.env.VISIT_TIMEOUT_MS || "15000", 10),
  dwellMs: parseInt(process.env.DWELL_MS || "3000", 10),
  allowedProtocols: ["http:", "https:"],
  cdpPort: parseInt(process.env.CDP_PORT || "9222", 10),
  cdpAllowOrigin: process.env.CDP_ALLOW_ORIGIN || "http://localhost:8080",
};

let busy = false;
const queue = [];

function enqueueVisit(targetUrl) {
  return new Promise((resolve, reject) => {
    queue.push({ targetUrl, resolve, reject });
    drainQueue();
  });
}

async function drainQueue() {
  if (busy) return;
  const job = queue.shift();
  if (!job) return;
  busy = true;
  try {
    job.resolve(await visit(job.targetUrl));
  } catch (err) {
    job.reject(err);
  } finally {
    busy = false;
    drainQueue();
  }
}

async function visit(targetUrl) {
  const browser = await puppeteer.launch({
    executablePath: CONFIG.chromiumPath,
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-web-security",
      "--disable-gpu",
      `--remote-debugging-port=${CONFIG.cdpPort}`,
      `--remote-allow-origins=${CONFIG.cdpAllowOrigin}`,
    ],
    userDataDir: "/tmp/chromium-profile",
    env: { ...process.env, HOME: "/tmp" },
  });

  try {
    const page = await browser.newPage();

    await page.goto(targetUrl, {
      waitUntil: "networkidle2",
      timeout: CONFIG.visitTimeoutMs,
    });

    await new Promise((r) => setTimeout(r, CONFIG.dwellMs));
  } finally {
    await browser.close();
  }
}

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function isBoring(req) {
  if (!("boring" in req.query)) return false;
  const v = req.query.boring;
  return v !== "0" && v !== "false" && v !== "no";
}

const BOT_FORM = `
<div class="botbox">
  <h2 class="rainbow rainbow_text_animated">SEND A URL 2 THE MONKE ADMIN</h2>
  <form method="post" action="/submit">
    <input type="url" name="url" placeholder="https://..." required>
    <button type="submit">YEET IT 2 ADMIN</button>
  </form>
</div>`;

const DEFAULT_MESSAGE = "ALL SYSTEMS SECURE, DEFINITELY NO XSS HERE";

const TAGLINE = `<h1 class="rainbow rainbow_text_animated">THE MOST SECURE XSS BOT OUT THERE</h1>`;

function messageHeader(message) {
  return `<h1 class="rainbow rainbow_text_animated"> STATUS: ${message} </h1>`;
}

function headers(message) {
  return `${TAGLINE}${messageHeader(message)}`;
}

const ASSET_DIR = path.join(__dirname, "public", "assets");
const ALL_ASSETS = fs.existsSync(ASSET_DIR) ? fs.readdirSync(ASSET_DIR).sort() : [];
const IMG_ASSETS = ALL_ASSETS.filter((f) => /\.(gif|jpe?g|png|webp|avif|bmp|svg|apng)$/i.test(f));
const AUDIO_ASSETS = ALL_ASSETS.filter((f) => /\.(mp3|wav|ogg|oga|m4a|flac|aac|opus)$/i.test(f));
const VIDEO_ASSETS = ALL_ASSETS.filter((f) => /\.(mp4|webm|mov|ogv|mkv|m4v)$/i.test(f));

const rint = (a, b) => Math.floor(Math.random() * (b - a + 1)) + a;
const pick = (arr) => arr[rint(0, arr.length - 1)];
const STORM_ANIMS = ["drift", "rotating", "moveImage", "zoom-in-zoom-out", "spinwarp", "wobbletext"];
const STORM_FILTERS = ["hue-rotate(90deg) saturate(5)", "invert(1)", "contrast(3)", "none", "blur(1px) saturate(6)", "sepia(1) hue-rotate(200deg)"];

function assetVideos() {
  return VIDEO_ASSETS.map(
    (f) =>
      `<video class="bgvid" preload="auto" loop muted playsinline><source src="/assets/${f}"></video>`
  ).join("\n");
}

function assetAudio() {
  return AUDIO_ASSETS.map(
    (f, i) =>
      `<audio id="autoaud${i}" class="autoaudio" preload="auto" loop><source src="/assets/${f}"></audio>`
  ).join("\n");
}

function assetStorm() {
  if (IMG_ASSETS.length === 0) return "";
  const count = Math.max(160, IMG_ASSETS.length * 12);
  const out = [];
  for (let n = 0; n < count; n++) {
    const f = IMG_ASSETS[n % IMG_ASSETS.length];
    const top = rint(-15, 95);
    const left = rint(-15, 95);
    const w = rint(50, 340);
    const dur = (rint(2, 24) + Math.random()).toFixed(2);
    const delay = (Math.random() * -30).toFixed(2);
    const anim = pick(STORM_ANIMS);
    const rot = rint(0, 359);
    const flt = pick(STORM_FILTERS);
    const z = rint(1, 6);
    out.push(
      `<img class="stormmonke" src="/assets/${f}" alt="monke" style="top:${top}vh;left:${left}vw;width:${w}px;z-index:${z};filter:${flt};transform:rotate(${rot}deg);animation:${anim} ${dur}s linear ${delay}s infinite">`
    );
  }
  return out.join("\n");
}

function marqueeStorm() {
  const lines = [
    "🚨 WARNING 🚨 THIS BOT IS SO SECURE IT HURTS 🚨 OOH OOH AHH AHH 🚨 BANANAS ENCRYPTED WITH AES-9000 🚨",
    "🤡 nothing to see here 🤡 definitely no reflected xss 🤡 please clap 🤡",
    "🙈 TRUST THE MONKE 🙉 THE MONKE IS LAW 🙊 ALL HAIL THE MONKE 🐒🐒🐒",
    "💀 ABANDON HOPE ALL YE WHO SCROLL HERE 💀 THE MONKE SEES ALL 💀",
    "📈 STONKS 📉 STONKS 📈 STONKS 📉 WHY IS IT SPINNING 📈 MAKE IT STOP 📉",
  ];
  const dirs = ["left", "right", "up", "down", "alternate"];
  return lines
    .map(
      (t) =>
        `<marquee ${pick(["", 'behavior="alternate"', `direction="${pick(dirs)}"`])} scrollamount="${rint(12, 40)}">${t}</marquee>`
    )
    .join("\n");
}

function crazyPage(innerHeaders, innerContent) {
  return `<!--
Code was stolen and adapted from https://github.com/DBprassan12/DUCTF4MEME
Thank them for making the original masterpiece
All I have done is made it way worse
I hope god forgives my sins in the future

2025 update
this code gets way more cursed each time I update it...
please help me....

2026 update
AI has made this worst.... oh god
-->
<!DOCTYPE html>
<html lang="en">
   <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet" href="/css/styles.css">
      <title>The most secure XSS bot out there</title>
   </head>
   <body>
      <div id="chaoszone">
      ${assetVideos()}
      <div class="seal">100% SECURE<br>CERTIFIED<br>NO BUGS</div>
      <div class="scroller top">🙈 THE MOST SECURE XSS BOT OUT THERE 🙉 NO HACKERS ALLOWED 🙊 YOUR DATA IS SAFE WITH THE MONKE 🍌🍌🍌 </div>
      <div class="scroller bottom">💸 STONKS ONLY GO UP 📈 TRUST THE MONKE 🐒 ZERO VULNERABILITIES DETECTED (probably) 🔒🔒🔒 </div>
      <div class="warnbanner">⚠ MAXIMUM SECURITY ENGAGED ⚠ DO NOT ATTEMPT TO HACK THE MONKE ⚠</div>
      ${marqueeStorm()}
      ${assetStorm()}
      <div class="firework"></div>
      <div class="firework"></div>
      <div class="firework"></div>
      <div class="firework"></div>
      </div>
      <div class="container-fluid">
         <div class="row">
            <div class="col-md-12">
               <div id="logo">
                  <img src="/assets/monkey-music-monkey.gif" alt="Description of the image">
               </div>
            </div>
         </div>
         <div class="row">
            <div class="col-md-12">
               <div id="memeContainer"></div>
               <button id="removeButton">👉 CLICK HERE 2 ENABLE MAXIMUM SECURITY 👈</button>
            </div>
         </div>
      </div>
      </div>
      <div class="meme">
        <video id="xssbot-vid" loop="">
            <!-- video from https://www.youtube.com/watch?v=xAT0hqeqbak -->
            <source src="/assets/stonks.mp4" type="video/mp4" />
        </video>
         <div class="row">
            <div class="col-md-12 rotating">
               ${innerHeaders}
               <div id="tsparticles"></div>
               <img class="monkes monek1" src="/assets/monke3.gif" alt="u mad?" />
               <img class="monkes monek2" src="/assets/monke4.gif" alt="monke activate" />
               <img class="monkes monek3" src="/assets/monke8.jpg" alt="ooh ooh ahhh ahH AHH!" />
               <img class="monkes monek4" src="/assets/monke9.jpg" alt="00111010101001011110" />
               <img class="monkes monek7" src="/assets/monke11.gif" alt="big mac" />
               <img class="monkes monek8" src="/assets/monke3.gif" alt="big mac" />
               <img class="monkes monek9" src="/assets/monke4.gif" alt="big mac" />
               <img class="monkes monek11" src="/assets/monke8.jpg" alt="big mac" />

               <img class=" msp1 rotate" src="/assets/spin1.gif" alt="monday" />
               <img class=" msp2 rotate" src="/assets/spin3.gif" alt="monday" />
               <img class=" msp3 rotate" src="/assets/spin4.gif" alt="monday" />
               <img class=" msp4 rotate" src="/assets/spin5.gif" alt="monday" />
               <img class=" msp5 rotate" src="/assets/spin6.gif" alt="monday" />
               <img class=" msp6 rotate" src="/assets/spin1.gif" alt="monday" />

               <img class="musicmonke" src="/assets/monkey-music-monkey.gif" alt="monke">

               <div class="firework"></div>
               <div class="firework"></div>
               <div class="firework"></div>


            </div>
            ${innerContent}
         </div>
      </div>
      </div>
      <audio id="monkenoise" loop>
         <source src="/assets/angry.mp3" type="audio/mpeg">
      </audio>
      <audio id="monday" loop>
        <source src="/assets/mondaysound.mp3" type="audio/mpeg">
     </audio>
     <audio id="audio1" loop>
      <source src="/assets/morebass.mp3" type="audio/mpeg">
      </audio>
      <audio id="audio2" loop>
         <source src="/assets/morechaos.mp3" type="audio/mpeg">
         </audio>
      ${assetAudio()}
      <script src="/js/script.js"></script>
   </body>
</html>`;
}

function boringPage(innerHeaders, innerContent) {
  return `<!DOCTYPE html>
<html lang="en">
   <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet" href="/css/styles.css">
      <title>The most secure XSS bot out there</title>
   </head>
   <body style="animation:none;cursor:auto">
      ${innerHeaders}
      ${innerContent}
   </body>
</html>`;
}

function render(req, innerHeaders, innerContent) {
  return isBoring(req)
    ? boringPage(innerHeaders, innerContent)
    : crazyPage(innerHeaders, innerContent);
}

const app = express();
app.use(express.urlencoded({ extended: false }));
app.use(express.static(path.join(__dirname, "public")));

app.get("/", (req, res) => {
  const message =
    req.query.message != null ? String(req.query.message) : DEFAULT_MESSAGE;
  res.type("html").send(render(req, headers(message), BOT_FORM));
});

app.post("/submit", async (req, res) => {
  const raw = (req.body.url || "").trim();

  let parsed;
  try {
    parsed = new URL(raw);
  } catch {
    return res
      .status(400)
      .type("html")
      .send(
        render(
          req,
          headers(DEFAULT_MESSAGE),
          `<div class="msg">that aint a url bro: ${esc(raw)}</div>${BOT_FORM}`
        )
      );
  }
  if (!CONFIG.allowedProtocols.includes(parsed.protocol)) {
    return res
      .status(400)
      .type("html")
      .send(
        render(
          req,
          headers(DEFAULT_MESSAGE),
          `<div class="msg">only http:// and https:// u silly monke</div>${BOT_FORM}`
        )
      );
  }

  try {
    await enqueueVisit(parsed.toString());
    res
      .type("html")
      .send(
        render(
          req,
          headers(DEFAULT_MESSAGE),
          `<div class="msg">the monke admin visited ur url ooh ooh ahh ahh</div>${BOT_FORM}`
        )
      );
  } catch (err) {
    console.error(`[bot] visit failed: ${err.message}`);
    res
      .status(500)
      .type("html")
      .send(
        render(
          req,
          headers(DEFAULT_MESSAGE),
          `<div class="msg">the monke admin fell over. try again.</div>${BOT_FORM}`
        )
      );
  }
});

app.get("/healthz", (_req, res) => res.type("text").send("ok"));

app.listen(CONFIG.port, "0.0.0.0", () => {
  console.log(`[bot] listening on :${CONFIG.port}`);
});
