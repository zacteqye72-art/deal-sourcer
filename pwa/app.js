// Claudio PWA — connects to /stream over WS, drives <audio> for music and a
// second <audio> for the DJ's voice. Talks to the server via the 6 endpoints
// in the HTTP contract.

const $ = (sel) => document.querySelector(sel);

const audio = $('#audio');
const speech = $('#speech');
const titleEl = $('#title');
const artistEl = $('#artist');
const reasonEl = $('#reason');
const sayEl = $('#say');
const playBtn = $('#playpause');
const skipBtn = $('#skip');
const chatForm = $('#chat');
const chatInput = $('#chat-input');

let currentNow = null;

// ── tabs ──────────────────────────────────────────────────────────────────

document.querySelectorAll('.tabs button').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tabs button').forEach((b) => b.classList.remove('active'));
    document.querySelectorAll('.pane').forEach((p) => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
    if (btn.dataset.tab === 'profile') loadTaste();
    if (btn.dataset.tab === 'settings') loadSettings();
  });
});

// ── now-playing rendering ─────────────────────────────────────────────────

function renderNow(now) {
  currentNow = now;
  if (!now || !now.url) {
    titleEl.textContent = '— 还没在播 —';
    artistEl.textContent = '';
    reasonEl.textContent = '';
    return;
  }
  titleEl.textContent = now.title || '(unknown)';
  artistEl.textContent = now.artist || '';
  reasonEl.textContent = now.reason || '';

  if (audio.src !== now.url) {
    audio.src = now.url;
    audio.play().catch(() => {/* needs user gesture */});
  }
  $('#now-snapshot').textContent = `${now.title} — ${now.artist}`;
}

function renderSay(now) {
  if (!now) return;
  if (now.say_text) sayEl.textContent = '“' + now.say_text + '”';
  else sayEl.textContent = '';
  if (now.say_url && speech.src !== location.origin + now.say_url) {
    speech.src = now.say_url;
    speech.play().catch(() => {});
  }
}

// ── WebSocket ─────────────────────────────────────────────────────────────

function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/stream`);
  $('#ws-state').textContent = 'connecting…';

  ws.addEventListener('open', () => { $('#ws-state').textContent = 'open'; });
  ws.addEventListener('close', () => {
    $('#ws-state').textContent = 'closed (retry 3s)';
    setTimeout(connectWS, 3000);
  });
  ws.addEventListener('message', (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return; }
    if (msg.type === 'now') {
      renderNow(msg.payload);
      renderSay(msg.payload);
    }
    if (msg.type === 'control' && msg.payload === 'pause') audio.pause();
    if (msg.type === 'control' && msg.payload === 'resume') audio.play().catch(()=>{});
  });
}
connectWS();

// ── controls ──────────────────────────────────────────────────────────────

playBtn.addEventListener('click', async () => {
  if (audio.paused) {
    audio.play();
    playBtn.textContent = '⏸';
    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: '继续' }),
    });
  } else {
    audio.pause();
    playBtn.textContent = '▶';
    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: '暂停' }),
    });
  }
});

skipBtn.addEventListener('click', () => {
  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: '下一首' }),
  });
});

audio.addEventListener('play', () => { playBtn.textContent = '⏸'; });
audio.addEventListener('pause', () => { playBtn.textContent = '▶'; });

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = '';
  await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
});

// ── profile / settings panes ──────────────────────────────────────────────

async function loadTaste() {
  const r = await fetch('/api/taste');
  const data = await r.json();
  const root = $('#taste-files');
  root.innerHTML = '';
  for (const [name, body] of Object.entries(data)) {
    const card = document.createElement('div');
    card.className = 'file';
    card.innerHTML = `<h3>${name}</h3><pre></pre>`;
    card.querySelector('pre').textContent = body;
    root.appendChild(card);
  }
}

async function loadSettings() {
  $('#srv-url').textContent = location.origin;
  const r = await fetch('/api/health').then((x) => x.json()).catch(() => null);
  if (!r) return;
  const slots = $('#slots');
  slots.innerHTML = '';
  r.slots.forEach((s) => {
    const li = document.createElement('li');
    li.innerHTML = `<code>${s.time}</code> <span>${s.label}</span>`;
    slots.appendChild(li);
  });
}

// initial fetch of /now in case WS is slow
fetch('/now').then((r) => r.json()).then(renderNow).catch(() => {});

// register service worker
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}
