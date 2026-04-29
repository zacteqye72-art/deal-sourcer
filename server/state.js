// SQLite-backed state. Persists messages, plays, plan, prefs across restarts.

import Database from 'better-sqlite3';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.resolve(__dirname, '..', 'state.db');

const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');

db.exec(`
  CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at INTEGER NOT NULL
  );
  CREATE TABLE IF NOT EXISTS plays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ncm_id TEXT,
    title TEXT,
    artist TEXT,
    started_at INTEGER NOT NULL,
    ended_at INTEGER,
    skipped INTEGER DEFAULT 0,
    feedback INTEGER DEFAULT 0
  );
  CREATE TABLE IF NOT EXISTS plan (
    day TEXT PRIMARY KEY,
    body TEXT NOT NULL,
    created_at INTEGER NOT NULL
  );
  CREATE TABLE IF NOT EXISTS prefs (
    key TEXT PRIMARY KEY,
    value TEXT
  );
`);

export const state = {
  appendMessage(role, content) {
    db.prepare(
      'INSERT INTO messages (role, content, created_at) VALUES (?, ?, ?)'
    ).run(role, content, Date.now());
  },

  recentMessages(limit = 20) {
    return db
      .prepare('SELECT role, content FROM messages ORDER BY id DESC LIMIT ?')
      .all(limit)
      .reverse();
  },

  startPlay({ ncm_id, title, artist }) {
    const info = db
      .prepare(
        'INSERT INTO plays (ncm_id, title, artist, started_at) VALUES (?, ?, ?, ?)'
      )
      .run(ncm_id ?? null, title ?? null, artist ?? null, Date.now());
    return info.lastInsertRowid;
  },

  endPlay(id, { skipped = false } = {}) {
    db.prepare(
      'UPDATE plays SET ended_at = ?, skipped = ? WHERE id = ?'
    ).run(Date.now(), skipped ? 1 : 0, id);
  },

  feedbackOnPlay(id, value) {
    db.prepare('UPDATE plays SET feedback = ? WHERE id = ?').run(value, id);
  },

  recentPlays(limit = 30) {
    return db
      .prepare(
        'SELECT id, ncm_id, title, artist, started_at, ended_at, skipped, feedback FROM plays ORDER BY id DESC LIMIT ?'
      )
      .all(limit);
  },

  skipRate(windowSize = 5) {
    const rows = db
      .prepare('SELECT skipped FROM plays ORDER BY id DESC LIMIT ?')
      .all(windowSize);
    if (rows.length === 0) return 0;
    return rows.filter((r) => r.skipped).length / rows.length;
  },

  savePlan(day, body) {
    db.prepare(
      'INSERT OR REPLACE INTO plan (day, body, created_at) VALUES (?, ?, ?)'
    ).run(day, JSON.stringify(body), Date.now());
  },

  getPlan(day) {
    const row = db.prepare('SELECT body FROM plan WHERE day = ?').get(day);
    return row ? JSON.parse(row.body) : null;
  },

  setPref(key, value) {
    db.prepare('INSERT OR REPLACE INTO prefs (key, value) VALUES (?, ?)').run(
      key,
      JSON.stringify(value)
    );
  },

  getPref(key, fallback = null) {
    const row = db.prepare('SELECT value FROM prefs WHERE key = ?').get(key);
    return row ? JSON.parse(row.value) : fallback;
  },
};
