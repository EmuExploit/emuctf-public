const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const express = require('express');
const Database = require('better-sqlite3');

const HOST = '127.0.0.1';
const PORT = Number(process.env.INTERNAL_API_PORT || 3000);
const API_KEY = process.env.INTERNAL_API_KEY || 'placeholder_internal_api_key';
const FLAG = process.env.flag || process.env.FLAG || 'EMU{real_flag_on_deployed}';
const DB_PATH = path.join(__dirname, '..', 'db', 'emus.db');
const MUGSHOT_DIR = path.join(__dirname, 'mugshots');

const EXPECTED_AUTH = `Bearer ${API_KEY}`;

const IMAGE_TYPES = {
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
};
const MUGSHOTS = new Map();
for (const entry of fs.readdirSync(MUGSHOT_DIR, { withFileTypes: true })) {
  const type = IMAGE_TYPES[path.extname(entry.name).toLowerCase()];
  if (entry.isFile() && type) MUGSHOTS.set(entry.name, type);
}

const db = new Database(DB_PATH, { readonly: true, fileMustExist: true });

const app = express();
app.disable('x-powered-by');
app.disable('etag');

function safeEqual(a, b) {
  const ab = Buffer.from(String(a));
  const bb = Buffer.from(String(b));
  if (ab.length !== bb.length) {
    crypto.timingSafeEqual(ab, ab);
    return false;
  }
  return crypto.timingSafeEqual(ab, bb);
}

app.use((req, res, next) => {
  const header = req.get('authorization') || '';
  if (!safeEqual(header, EXPECTED_AUTH)) {
    return res.status(401).json({ error: 'unauthorized' });
  }
  next();
});

app.get('/api/emus', (req, res) => {
  const emus = db
    .prepare('SELECT id, name, status, prize, danger, mugshot FROM emus ORDER BY id')
    .all();
  res.json({ emus });
});

app.get('/api/emus/:id', (req, res) => {
  const id = req.params.id;
  if (!/^[1-9][0-9]{0,8}$/.test(id)) {
    return res.status(400).json({ error: 'invalid emu id' });
  }
  const emu = db.prepare('SELECT * FROM emus WHERE id = ?').get(Number(id));
  if (!emu) return res.status(404).json({ error: 'emu not found' });
  res.json({ emu });
});

app.get('/api/mugshots/:file', (req, res) => {
  const file = req.params.file;
  const type = MUGSHOTS.get(file);
  if (!type) return res.status(404).json({ error: 'mugshot not found' });
  res.type(type).sendFile(file, { root: MUGSHOT_DIR });
});

app.get('/adminapi/flag', (req, res) => {
  res.json({ flag: FLAG });
});

app.use((req, res) => res.status(404).json({ error: 'not found' }));

app.listen(PORT, HOST, () => {
  console.log(`[internal] registry API listening on http://${HOST}:${PORT}`);
});
