// Scheduler.js — rhythm. Fires triggers at fixed wall-clock points and on
// hourly mood checks. Each fire calls back into the brain via `onTick`.
//
// Kept self-contained (no `node-cron` dep) — these are fixed daily slots.

const SLOTS = [
  { time: '07:00', label: 'morning-plan' },
  { time: '09:00', label: 'commute' },
  { time: '12:00', label: 'lunch' },
  { time: '14:00', label: 'mood-check' },
  { time: '18:00', label: 'evening' },
  { time: '22:30', label: 'wind-down' },
];

function nextFireAt(hhmm) {
  const [h, m] = hhmm.split(':').map(Number);
  const now = new Date();
  const fire = new Date(now);
  fire.setHours(h, m, 0, 0);
  if (fire <= now) fire.setDate(fire.getDate() + 1);
  return fire;
}

export function startScheduler({ onTick }) {
  const timers = [];

  function arm(slot) {
    const at = nextFireAt(slot.time);
    const delay = at - Date.now();
    const t = setTimeout(() => {
      Promise.resolve()
        .then(() => onTick({ trigger: `slot:${slot.label}` }))
        .catch((e) => console.error('[scheduler] slot fire error', e));
      arm(slot); // re-arm for tomorrow
    }, delay);
    timers.push(t);
  }

  SLOTS.forEach(arm);

  // Hourly mood check, on the half hour to avoid colliding with slots.
  const hourly = setInterval(() => {
    onTick({ trigger: 'hourly:mood-check' }).catch((e) =>
      console.error('[scheduler] hourly fire error', e)
    );
  }, 60 * 60 * 1000);
  timers.push(hourly);

  return () => timers.forEach(clearTimeout);
}

export const SCHEDULER_SLOTS = SLOTS;
