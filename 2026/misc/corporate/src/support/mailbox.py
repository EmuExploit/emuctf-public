"""SQLite mailbox storage; callers own transaction boundaries."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from threading import Lock

from support.models import apply_automatic_rejection

SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    id TEXT PRIMARY KEY, created TEXT, client TEXT, stamp REAL,
    metadata TEXT, state TEXT NOT NULL DEFAULT 'new', summary TEXT
);
CREATE INDEX IF NOT EXISTS review_queue ON submissions(state, stamp DESC, id DESC);
CREATE INDEX IF NOT EXISTS submission_rate ON submissions(client, stamp);
CREATE TABLE IF NOT EXISTS review_login_attempts (client TEXT, stamp REAL);
CREATE TABLE IF NOT EXISTS submission_attempts (
    id TEXT PRIMARY KEY, client TEXT NOT NULL, stamp REAL NOT NULL,
    processing_until REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS attempt_rate ON submission_attempts(client, stamp);
CREATE TABLE IF NOT EXISTS submission_waiters (
    position INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT UNIQUE NOT NULL, expires REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS submission_source_attempts (client TEXT, stamp REAL);
CREATE INDEX IF NOT EXISTS source_rate ON submission_source_attempts(client, stamp);
"""


class Mailbox:
    def __init__(self, root):
        self.root = Path(root)
        self._initialized = False
        self._schema_lock = Lock()
        self._pending_screened = False
        self._screening_lock = Lock()

    def connect(self):
        # Multiple service processes may initialize the same volume. SQLite
        # serializes the idempotent DDL; this lock handles threads in this app.
        with self._schema_lock:
            if not self._initialized:
                self.root.mkdir(parents=True, exist_ok=True)
                with closing(sqlite3.connect(self.root / 'mailbox.sqlite', timeout=35)) as db:
                    db.executescript(SCHEMA)
                self._initialized = True
        return sqlite3.connect(self.root / 'mailbox.sqlite', timeout=35)

    def screen_pending_queue(self):
        with self._screening_lock:
            # Once per process, apply threshold decisions to already queued reports.
            # Read their saved signals in small batches; do not rescan any files.
            if self._pending_screened:
                return
            with closing(self.connect()) as db:
                db.execute('BEGIN IMMEDIATE')
                after = ''
                while True:
                    rows = db.execute(
                        "SELECT id, metadata FROM submissions WHERE state='new' AND id>? ORDER BY id LIMIT 50",
                        (after,),
                    ).fetchall()
                    if not rows:
                        break
                    for sid, raw in rows:
                        meta = json.loads(raw)
                        state = apply_automatic_rejection(meta)
                        if state:
                            db.execute(
                                'UPDATE submissions SET state=?, metadata=? WHERE id=?',
                                (state, json.dumps(meta), sid),
                            )
                    after = rows[-1][0]
                db.commit()
            self._pending_screened = True
