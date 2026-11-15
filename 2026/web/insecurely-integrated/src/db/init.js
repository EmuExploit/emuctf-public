const path = require('path');
const fs = require('fs');
const Database = require('better-sqlite3');

const DB_PATH = path.join(__dirname, 'emus.db');

for (const f of [DB_PATH, `${DB_PATH}-wal`, `${DB_PATH}-shm`, `${DB_PATH}-journal`]) {
  if (fs.existsSync(f)) fs.unlinkSync(f);
}

const db = new Database(DB_PATH);
db.pragma('journal_mode = DELETE');

db.exec(`
  CREATE TABLE emus (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    status    TEXT NOT NULL,
    prize     INTEGER NOT NULL,
    danger    TEXT NOT NULL,
    crimes    TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    notes     TEXT NOT NULL,
    mugshot   TEXT NOT NULL
  );
`);

const emus = [
  {
    name: 'toasterpwn',
    status: 'WANTED — DEAD OR ALIVE',
    prize: 25000,
    danger: 'Extreme',
    crimes: 'Leader of Emu Exploit, hacked the Prime Minister\'s toaster',
    last_seen: 'Kings Park rose garden, harassing tourists for chips.',
    notes: 'Do not bring any toasters while confronting',
    mugshot: 'toasterpwn.webp'
  },
  {
    name: 'TheSavageTeddy',
    status: 'WANTED — DEAD OR ALIVE',
    prize: 42000,
    danger: 'Extreme',
    crimes: 'Wanted by Interpol for terrorising France, bypassing border control and touching paintings at the Louvre with his grubby feathers',
    last_seen: 'Loitering outside the Fremantle markets fish stall.',
    notes: 'WILL HACK ANYTHING',
    mugshot: 'TheSavageTeddy.png'
  },
  {
    name: 'torry2',
    status: 'WANTED — ALIVE ONLY',
    prize: 18500,
    danger: 'High',
    crimes: 'Leader of all ducks, responsible for multiple firebombings',
    last_seen: 'Sprinting down James Street at 3am, kebab in beak.',
    notes: 'He hides as a duck.',
    mugshot: 'torry2.png'
  },
  {
    name: 'mc fat monke',
    status: 'WANTED — DEAD ONLY',
    prize: 6900000,
    danger: 'Extreme Extreme',
    crimes: 'Established a Banana Republic to feed his own addiction, also writes bad rap songs',
    last_seen: 'Reclining in a deckchair at Cottesloe Beach wearing stolen sunglasses.',
    notes: 'DO NOT ALLOW TO RAP! CAUSES IMMEDIATE BRAIN HEMORRHAGE AND MAKES YOU ENJOY AI SLOP!',
    mugshot: 'mc-fat-monke.jpg'
  }
];

const MUGSHOT_DIR = path.join(__dirname, '..', 'internal', 'mugshots');
for (const emu of emus) {
  if (!fs.existsSync(path.join(MUGSHOT_DIR, emu.mugshot))) {
    throw new Error(`[db] missing mugshot for ${emu.name}: ${emu.mugshot}`);
  }
}

const insert = db.prepare(
  `INSERT INTO emus (name, status, prize, danger, crimes, last_seen, notes, mugshot)
   VALUES (@name, @status, @prize, @danger, @crimes, @last_seen, @notes, @mugshot)`
);
const insertAll = db.transaction((rows) => rows.forEach((r) => insert.run(r)));
insertAll(emus);

const count = db.prepare('SELECT COUNT(*) AS n FROM emus').get().n;
db.close();
console.log(`[db] built ${DB_PATH} with ${count} emus`);
