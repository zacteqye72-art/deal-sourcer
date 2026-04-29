// Claudio server entry. Express HTTP + WS, plus the scheduler.
//
// HTTP contract (PWA ↔ server, the 6 lines from the diagram):
//   GET  /now                    current playing state
//   GET  /api/taste              user corpus (taste.md, etc.)
//   POST /api/chat               user message → Claude → DJ envelope
//   GET  /api/plan/today         today's plan (cached in state.db)
//   POST /api/feedback           👍/👎 / skip a play row
//   WS   /stream                 push: now-playing, say, plan updates
//
// Static:
//   GET  /tts/<hash>.mp3         cached Fish Audio output
//   GET  /                       PWA shell (pwa/index.html)

import 'dotenv/config';

import express from 'express';
import http from 'node:http';
import path from 'node:path';
import fs from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { WebSocketServer } from 'ws';

import { state } from './state.js';
import { buildContext } from './context.js';
import { think } from './claude.js';
import { route } from './router.js';
import { synthesise, TTS_DIR } from './tts.js';
import { startScheduler, SCHEDULER_SLOTS } from './scheduler.js';
import { netease } from './adapters/netease.js';
import { upnp } from './adapters/upnp.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const PORT = Number(process.env.PORT) || 8080;

const app = express();
app.use(express.json({ limit: '256kb' }));
app.use(express.static(path.join(ROOT, 'pwa'), { extensions: ['html'] }));
app.use('/tts', express.static(TTS_DIR, { maxAge: '7d' }));

// In-memory mirror of what's playing. Single user, single device — fine.
const nowPlaying = {
  ncm_id: null,
  title: null,
  artist: null,
  url: null,
  say_url: null,
  say_text: null,
  reason: null,
  started_at: null,
  play_row_id: null,
};

// ── core decision loop ────────────────────────────────────────────────────

async function decide({ userInput = '', trigger = 'manual', toolResult = null } = {}) {
  if (userInput) state.appendMessage('user', userInput);
  const ctx = await buildContext({ userInput, trigger, toolResult });
  const envelope = await think(ctx);
  state.appendMessage('assistant', JSON.stringify(envelope));
  return envelope;
}

async function resolvePlayQueue(queries) {
  const out = [];
  for (const q of queries) {
    const hits = await netease.search(q.query).catch(() => []);
    if (!hits.length) continue;
    const top = hits[0];
    const url = await netease.songUrl(top.ncm_id).catch(() => null);
    if (!url) continue;
    out.push({ ...top, url, reason: q.reason });
  }
  return out;
}

async function broadcastEnvelope(envelope) {
  let say = null;
  if (envelope.say) {
    say = await synthesise(envelope.say).catch((e) => {
      console.warn('[tts] failed:', e.message);
      return null;
    });
  }

  const queue = await resolvePlayQueue(envelope.play || []);
  const first = queue[0];

  if (first) {
    if (nowPlaying.play_row_id) {
      state.endPlay(nowPlaying.play_row_id, { skipped: false });
    }
    nowPlaying.ncm_id = first.ncm_id;
    nowPlaying.title = first.title;
    nowPlaying.artist = first.artist;
    nowPlaying.url = first.url;
    nowPlaying.reason = envelope.reason;
    nowPlaying.started_at = Date.now();
    nowPlaying.play_row_id = state.startPlay({
      ncm_id: first.ncm_id,
      title: first.title,
      artist: first.artist,
    });
    upnp.play(first.url, { title: first.title, artist: first.artist }).catch(() => {});
  }

  nowPlaying.say_url = say?.url ?? null;
  nowPlaying.say_text = envelope.say || null;

  pushAll({ type: 'now', payload: nowPlaying, queue, envelope });
  return { envelope, queue, say };
}

// ── HTTP endpoints ────────────────────────────────────────────────────────

app.get('/now', (_req, res) => {
  res.json(nowPlaying);
});

app.get('/api/taste', async (_req, res) => {
  const files = ['taste.md', 'routines.md', 'mood-rules.md', 'playlists.json'];
  const out = {};
  for (const f of files) {
    try {
      out[f] = await fs.readFile(path.join(ROOT, 'user', f), 'utf8');
    } catch {
      out[f] = '';
    }
  }
  res.json(out);
});

app.post('/api/chat', async (req, res) => {
  const input = (req.body?.text || '').toString();
  const routed = await route(input);

  if (routed.handled && routed.result?.control) {
    const c = routed.result.control;
    if (c === 'pause') await upnp.pause();
    if (c === 'resume') await upnp.resume();
    if (c === 'skip' && nowPlaying.play_row_id) {
      state.endPlay(nowPlaying.play_row_id, { skipped: true });
      nowPlaying.play_row_id = null;
    }
    pushAll({ type: 'control', payload: c });
    return res.json({ ok: true, control: c });
  }

  const envelope = await decide({
    userInput: input,
    trigger: 'chat',
    toolResult: routed.handled ? routed.result : null,
  });
  const broadcast = await broadcastEnvelope(envelope);
  res.json({ ok: true, ...broadcast });
});

app.get('/api/plan/today', (_req, res) => {
  const day = new Date().toISOString().slice(0, 10);
  res.json({ day, plan: state.getPlan(day) });
});

app.post('/api/feedback', (req, res) => {
  const { play_id, value } = req.body || {};
  if (!play_id || typeof value !== 'number') {
    return res.status(400).json({ ok: false, error: 'play_id and value required' });
  }
  state.feedbackOnPlay(play_id, value);
  res.json({ ok: true });
});

app.get('/api/health', (_req, res) => {
  res.json({
    ok: true,
    now: new Date().toISOString(),
    slots: SCHEDULER_SLOTS,
    has_now_playing: Boolean(nowPlaying.url),
  });
});

// ── WebSocket /stream ─────────────────────────────────────────────────────

const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: '/stream' });
const sockets = new Set();

wss.on('connection', (ws) => {
  sockets.add(ws);
  ws.send(JSON.stringify({ type: 'now', payload: nowPlaying }));
  ws.on('close', () => sockets.delete(ws));
});

function pushAll(msg) {
  const data = JSON.stringify(msg);
  for (const ws of sockets) {
    try {
      ws.send(data);
    } catch {
      /* socket already gone */
    }
  }
}

// ── scheduler tick ────────────────────────────────────────────────────────

startScheduler({
  onTick: async ({ trigger }) => {
    console.log(`[scheduler] tick ${trigger}`);
    const envelope = await decide({ trigger });
    if (trigger === 'slot:morning-plan') {
      const day = new Date().toISOString().slice(0, 10);
      state.savePlan(day, envelope);
      state.setPref('last_plan_day', day);
    }
    await broadcastEnvelope(envelope);
  },
});

// ── boot ──────────────────────────────────────────────────────────────────

server.listen(PORT, () => {
  console.log(`Claudio listening on http://localhost:${PORT}`);
});
