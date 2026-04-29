// Claude.js — brain adapter. Spawns the `claude` CLI as a subprocess with
// `-p --output-format json`, so we lean on the Max subscription for auth and
// don't need an API key. Falls back to a deterministic stub if the CLI is
// missing, so the rest of the system stays runnable in dev.

import { spawn } from 'node:child_process';
import { renderPrompt } from './context.js';

const CLAUDE_BIN = process.env.CLAUDE_BIN || 'claude';
const CLAUDE_MODEL = process.env.CLAUDE_MODEL || 'claude-sonnet-4-6';

/**
 * Run Claude on an assembled context. Returns the parsed DJ envelope:
 *   { say, play: [{query, reason}], reason, segue }
 */
export async function think(ctx) {
  const prompt = renderPrompt(ctx);
  let raw;
  try {
    raw = await runClaude(prompt);
  } catch (err) {
    console.warn('[claude] CLI unavailable, using stub:', err.message);
    return stubDecision(ctx);
  }
  return parseEnvelope(raw, ctx);
}

function runClaude(prompt) {
  return new Promise((resolve, reject) => {
    const args = ['-p', '--output-format', 'json', '--model', CLAUDE_MODEL];
    const proc = spawn(CLAUDE_BIN, args, { stdio: ['pipe', 'pipe', 'pipe'] });

    let stdout = '';
    let stderr = '';
    proc.stdout.on('data', (b) => (stdout += b.toString()));
    proc.stderr.on('data', (b) => (stderr += b.toString()));
    proc.on('error', reject);
    proc.on('close', (code) => {
      if (code !== 0) return reject(new Error(`claude exit ${code}: ${stderr}`));
      resolve(stdout);
    });

    proc.stdin.write(prompt);
    proc.stdin.end();
  });
}

// Claude CLI's JSON output wraps the assistant reply. Pull out the inner JSON
// the persona was instructed to emit.
function parseEnvelope(raw, ctx) {
  let outer;
  try {
    outer = JSON.parse(raw);
  } catch {
    return parseInnerJson(raw) ?? stubDecision(ctx);
  }
  const inner = outer.result ?? outer.text ?? outer.completion ?? raw;
  return parseInnerJson(inner) ?? stubDecision(ctx);
}

function parseInnerJson(text) {
  if (typeof text !== 'string') return null;
  // Tolerate ```json ... ``` fences if the model added them.
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  const body = fenced ? fenced[1] : text;
  const start = body.indexOf('{');
  const end = body.lastIndexOf('}');
  if (start === -1 || end === -1) return null;
  try {
    const obj = JSON.parse(body.slice(start, end + 1));
    if (typeof obj === 'object' && obj !== null) return normalize(obj);
  } catch {
    return null;
  }
  return null;
}

function normalize(obj) {
  return {
    say: typeof obj.say === 'string' ? obj.say : '',
    play: Array.isArray(obj.play) ? obj.play.slice(0, 3) : [],
    reason: typeof obj.reason === 'string' ? obj.reason : '',
    segue: obj.segue ?? null,
  };
}

// Used when the Claude CLI isn't installed. Deterministic, but at least
// honours the user's anchor playlists so the player can demo end-to-end.
function stubDecision(ctx) {
  const hour = new Date().getHours();
  const slot =
    hour < 9 ? 'weekday-morning'
    : hour < 12 ? 'coding'
    : hour < 18 ? 'rainy'
    : hour < 22 ? 'coding'
    : 'pre-sleep';

  const seeds = {
    'weekday-morning': ['山下達郎 Sparkle', '竹内まりや Plastic Love'],
    'coding': ['Mono Ashes in the Snow', '惘闻 黄昏'],
    'rainy': ['坂本龍一 Merry Christmas Mr. Lawrence', 'Nils Frahm Says'],
    'pre-sleep': ['Erik Satie Gymnopédie No.1', 'Chopin Nocturne Op.9 No.2'],
  }[slot];

  return {
    say: hour < 9
      ? '早。今天先来一段 city pop 醒醒神。'
      : hour >= 22
        ? ''
        : '换一段你最近没听过的吧。',
    play: seeds.map((q) => ({ query: q, reason: `stub:${slot}` })),
    reason: `stub fallback @${slot}`,
    segue: null,
  };
}
