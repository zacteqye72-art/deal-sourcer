// Router.js — intent fan-out. Cheap, rule-based; not the Claude call.
//
// Layer-2 ROUTER: keep the brain warm by short-circuiting trivial commands
// that don't need the model.
//
//   "下一首" / "skip"          → ncm.skip
//   "暂停" / "pause"            → upnp.pause
//   "搜 山下達郎"                → ncm.search (return raw hits)
//   anything else               → forward to claude.think()

import { netease } from './adapters/netease.js';

const RULES = [
  { match: /^(下一首|skip|next)$/i, intent: 'skip' },
  { match: /^(暂停|pause)$/i, intent: 'pause' },
  { match: /^(继续|resume|play)$/i, intent: 'resume' },
  { match: /^(音量\s*[+\-]?\d+|volume\s+\d+)$/i, intent: 'volume' },
  { match: /^搜\s+(.+)/i, intent: 'search', captureGroup: 1 },
];

export function classify(input) {
  if (!input || typeof input !== 'string') return { intent: 'chat' };
  const trimmed = input.trim();
  for (const rule of RULES) {
    const m = trimmed.match(rule.match);
    if (m) {
      return {
        intent: rule.intent,
        arg: rule.captureGroup ? m[rule.captureGroup] : trimmed,
      };
    }
  }
  return { intent: 'chat', arg: trimmed };
}

/**
 * Run a routed intent. Returns either:
 *   { handled: true, result }     — short-circuit, no Claude call needed
 *   { handled: false, search? }   — fall through to Claude, optionally with
 *                                   pre-fetched search results to inject
 */
export async function route(input) {
  const { intent, arg } = classify(input);

  switch (intent) {
    case 'skip':
    case 'pause':
    case 'resume':
    case 'volume':
      return { handled: true, result: { control: intent, arg } };

    case 'search': {
      const hits = await netease.search(arg).catch(() => []);
      return { handled: true, result: { search: arg, hits } };
    }

    case 'chat':
    default:
      return { handled: false };
  }
}
