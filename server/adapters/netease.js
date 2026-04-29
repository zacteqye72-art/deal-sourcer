// NetEaseCloudMusicApi adapter.
// Expects a local instance of https://github.com/Binaryify/NeteaseCloudMusicApi
// running at NCM_BASE_URL (default http://127.0.0.1:3000).

const BASE = process.env.NCM_BASE_URL || 'http://127.0.0.1:3000';

async function get(pathname, params = {}) {
  const url = new URL(pathname, BASE);
  for (const [k, v] of Object.entries(params)) {
    if (v != null) url.searchParams.set(k, String(v));
  }
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(`ncm ${pathname} -> ${res.status}`);
  return res.json();
}

export const netease = {
  /** Search and return up to 5 lightweight hits. */
  async search(keywords) {
    const data = await get('/search', { keywords, limit: 5 });
    const songs = data?.result?.songs ?? [];
    return songs.map((s) => ({
      ncm_id: String(s.id),
      title: s.name,
      artist: (s.artists || []).map((a) => a.name).join(' / '),
      album: s.album?.name,
      duration_ms: s.duration,
    }));
  },

  /** Resolve a direct stream URL for a given ncm_id. */
  async songUrl(id) {
    const data = await get('/song/url/v1', { id, level: 'standard' });
    const url = data?.data?.[0]?.url;
    return url || null;
  },

  /** LRC lyrics if available. */
  async lyric(id) {
    const data = await get('/lyric', { id });
    return data?.lrc?.lyric || '';
  },

  /** Daily recommendation pool — used by the scheduler when cold. */
  async recommend(limit = 10) {
    try {
      const data = await get('/recommend/songs');
      return (data?.data?.dailySongs || []).slice(0, limit).map((s) => ({
        ncm_id: String(s.id),
        title: s.name,
        artist: (s.ar || []).map((a) => a.name).join(' / '),
      }));
    } catch {
      return [];
    }
  },

  /** Songs from a given playlist id (number-as-string). */
  async playlistTracks(playlistId, limit = 20) {
    const data = await get('/playlist/track/all', {
      id: playlistId,
      limit,
      offset: 0,
    });
    const songs = data?.songs ?? [];
    return songs.map((s) => ({
      ncm_id: String(s.id),
      title: s.name,
      artist: (s.ar || []).map((a) => a.name).join(' / '),
      duration_ms: s.dt,
    }));
  },
};
