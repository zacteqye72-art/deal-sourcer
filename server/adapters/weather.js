// OpenWeather adapter. Cached for 10 minutes since weather doesn't change that
// fast and we'd rather not hammer the free tier.

const API = 'https://api.openweathermap.org/data/2.5/weather';
const TTL_MS = 10 * 60 * 1000;

let cache = { at: 0, payload: null };

export const weather = {
  async current() {
    const key = process.env.OPENWEATHER_API_KEY;
    if (!key) return null;
    if (cache.payload && Date.now() - cache.at < TTL_MS) return cache.payload;

    const lat = process.env.OPENWEATHER_LAT || '39.9042';
    const lon = process.env.OPENWEATHER_LON || '116.4074';
    const url = `${API}?lat=${lat}&lon=${lon}&units=metric&lang=zh_cn&appid=${key}`;

    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`openweather ${res.status}`);
      const data = await res.json();
      const payload = {
        temp_c: data.main?.temp,
        feels_like_c: data.main?.feels_like,
        pressure: data.main?.pressure,
        humidity: data.main?.humidity,
        condition: data.weather?.[0]?.description,
        wind_mps: data.wind?.speed,
      };
      cache = { at: Date.now(), payload };
      return payload;
    } catch (err) {
      console.warn('[weather] fetch failed:', err.message);
      return null;
    }
  },
};
