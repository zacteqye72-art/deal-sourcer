// Fish Audio TTS adapter (https://fish.audio).
// Returns a Buffer of MP3 bytes, or null when the API key is missing
// (so the rest of the system stays runnable in dev).

const API = 'https://api.fish.audio/v1/tts';

export const fish = {
  async tts(text) {
    const key = process.env.FISH_API_KEY;
    const voice = process.env.FISH_VOICE_ID;
    if (!key) {
      console.warn('[fish] FISH_API_KEY not set, skipping synthesis');
      return null;
    }

    const body = {
      text,
      reference_id: voice || undefined,
      format: 'mp3',
      mp3_bitrate: 128,
      latency: 'normal',
    };

    const res = await fetch(API, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${key}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      console.warn('[fish] tts failed', res.status, await res.text());
      return null;
    }
    return Buffer.from(await res.arrayBuffer());
  },
};
