// TTS.js — voice pipeline. Hashes the text, caches MP3s under cache/tts/,
// returns a URL the PWA can fetch. Hash means same line never re-synthesises.

import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { fish } from './adapters/fish.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CACHE_DIR = path.resolve(__dirname, '..', 'cache', 'tts');

await fs.mkdir(CACHE_DIR, { recursive: true });

function hashText(text) {
  return crypto.createHash('sha1').update(text).digest('hex').slice(0, 16);
}

/**
 * Synthesise `text` if not already cached. Returns a relative URL the PWA
 * can request: /tts/<hash>.mp3
 */
export async function synthesise(text) {
  if (!text || !text.trim()) return null;
  const hash = hashText(text);
  const file = path.join(CACHE_DIR, `${hash}.mp3`);

  try {
    await fs.access(file);
    return { url: `/tts/${hash}.mp3`, cached: true };
  } catch {
    /* not cached, synthesise */
  }

  const buf = await fish.tts(text);
  if (!buf) return null;
  await fs.writeFile(file, buf);
  return { url: `/tts/${hash}.mp3`, cached: false };
}

export const TTS_DIR = CACHE_DIR;
