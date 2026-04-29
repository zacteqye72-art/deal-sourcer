// Context.js — assembles the 6-fragment "context box" that gets pasted into
// every model call. Layer-3 of Claudio's architecture.
//
// The 6 fragments:
//   1. system prompt          (prompts/dj-persona.md)
//   2. user corpus            (user/*.md, user/*.json)
//   3. environment injection  (weather, calendar, now)
//   4. retrieved memory       (state.db: recent plays, prefs)
//   5. user input / tool result
//   6. execution trace        (scheduler trigger, webhook, etc.)

import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { state } from './state.js';
import { weather } from './adapters/weather.js';
import { feishu } from './adapters/feishu.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');

async function readIfExists(rel) {
  try {
    return await fs.readFile(path.join(ROOT, rel), 'utf8');
  } catch {
    return '';
  }
}

async function loadSystemPrompt() {
  return readIfExists('prompts/dj-persona.md');
}

async function loadUserCorpus() {
  const [taste, routines, mood, playlistsRaw] = await Promise.all([
    readIfExists('user/taste.md'),
    readIfExists('user/routines.md'),
    readIfExists('user/mood-rules.md'),
    readIfExists('user/playlists.json'),
  ]);
  return [
    `# taste.md\n${taste}`,
    `# routines.md\n${routines}`,
    `# mood-rules.md\n${mood}`,
    `# playlists.json\n${playlistsRaw}`,
  ].join('\n\n---\n\n');
}

async function loadEnvironment() {
  const now = new Date();
  const [w, cal] = await Promise.all([
    weather.current().catch(() => null),
    feishu.todayEvents().catch(() => []),
  ]);
  return {
    now: now.toISOString(),
    local_time: now.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }),
    weekday: now.toLocaleDateString('zh-CN', {
      weekday: 'long',
      timeZone: 'Asia/Shanghai',
    }),
    weather: w,
    calendar: cal,
  };
}

function loadMemory() {
  return {
    recent_plays: state.recentPlays(15),
    skip_rate_last_5: state.skipRate(5),
    last_plan_day: state.getPref('last_plan_day'),
  };
}

/**
 * Build the 6-fragment context box.
 *
 * @param {object} opts
 * @param {string} opts.userInput   user message or tool result text
 * @param {string} [opts.trigger]   what fired this turn (e.g. "scheduler:09:00")
 * @param {object} [opts.toolResult] structured tool output (e.g. ncm search hits)
 */
export async function buildContext({ userInput = '', trigger = 'manual', toolResult = null } = {}) {
  const [systemPrompt, userCorpus, environment] = await Promise.all([
    loadSystemPrompt(),
    loadUserCorpus(),
    loadEnvironment(),
  ]);
  const memory = loadMemory();

  return {
    systemPrompt,
    userCorpus,
    environment,
    memory,
    userInput,
    toolResult,
    trigger,
  };
}

/**
 * Render the assembled context box into a single prompt string for Claude.
 * Kept as plain text so it survives subprocess piping cleanly.
 */
export function renderPrompt(ctx) {
  const parts = [
    ctx.systemPrompt.trim(),
    '',
    '## ① 用户语料 (user/*)',
    ctx.userCorpus.trim(),
    '',
    '## ② 环境注入',
    JSON.stringify(ctx.environment, null, 2),
    '',
    '## ③ 已检索记忆 (state.db)',
    JSON.stringify(ctx.memory, null, 2),
    '',
  ];
  if (ctx.toolResult) {
    parts.push('## ④ 工具结果', JSON.stringify(ctx.toolResult, null, 2), '');
  }
  parts.push('## ⑤ 执行轨迹', `trigger=${ctx.trigger}`, '');
  parts.push('## ⑥ 用户输入', ctx.userInput || '(空)', '');
  parts.push(
    '---',
    '现在按 system 中要求，只输出 JSON ({say, play, reason, segue})。'
  );
  return parts.join('\n');
}
