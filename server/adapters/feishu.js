// Feishu / Lark adapter — reads today's calendar events.
// Uses the v3 calendar API. Requires a tenant access token or user token with
// calendar:event scope. Without credentials, returns [].

const TOKEN_URL = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal';
const FREE_BUSY_URL = 'https://open.feishu.cn/open-apis/calendar/v4/freebusy/list';

let tokenCache = { token: null, exp: 0 };

async function tenantToken() {
  if (tokenCache.token && Date.now() < tokenCache.exp) return tokenCache.token;
  const id = process.env.FEISHU_APP_ID;
  const secret = process.env.FEISHU_APP_SECRET;
  if (!id || !secret) return null;

  const res = await fetch(TOKEN_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ app_id: id, app_secret: secret }),
  });
  if (!res.ok) return null;
  const data = await res.json();
  if (!data.tenant_access_token) return null;
  tokenCache = {
    token: data.tenant_access_token,
    exp: Date.now() + (data.expire - 60) * 1000,
  };
  return tokenCache.token;
}

export const feishu = {
  /** Today's events (subset: title, start, end). [] if not configured. */
  async todayEvents() {
    // Prefer a long-lived user token (read-only), fallback to tenant token.
    const userToken = process.env.FEISHU_USER_ACCESS_TOKEN;
    const token = userToken || (await tenantToken());
    if (!token) return [];

    const start = new Date();
    start.setHours(0, 0, 0, 0);
    const end = new Date(start);
    end.setDate(end.getDate() + 1);

    try {
      const res = await fetch(FREE_BUSY_URL, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          time_min: start.toISOString(),
          time_max: end.toISOString(),
          user_id_list: ['me'],
        }),
      });
      if (!res.ok) return [];
      const data = await res.json();
      const busy = data?.data?.freebusy_list ?? [];
      return busy.map((b) => ({
        start: b.start_time,
        end: b.end_time,
        title: b.summary || '(busy)',
      }));
    } catch (err) {
      console.warn('[feishu] today events failed:', err.message);
      return [];
    }
  },
};
