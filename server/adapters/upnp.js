// UPnP AVTransport adapter — pushes a stream URL to a renderer on the LAN
// (e.g. Naim Mu-so, Sonos, any UPnP/DLNA receiver).
//
// This is a minimal SOAP client. Discovery uses SSDP if UPNP_RENDERER_URL
// isn't set; otherwise we use the URL directly as the AVTransport control URL.

import dgram from 'node:dgram';

const SSDP_ADDR = '239.255.255.250';
const SSDP_PORT = 1900;
const ST = 'urn:schemas-upnp-org:service:AVTransport:1';

function soapEnvelope(action, params) {
  const args = Object.entries(params)
    .map(([k, v]) => `<${k}>${escapeXml(String(v))}</${k}>`)
    .join('');
  return `<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:${action} xmlns:u="${ST}">${args}</u:${action}>
  </s:Body>
</s:Envelope>`;
}

function escapeXml(s) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function soap(controlUrl, action, params) {
  const res = await fetch(controlUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'text/xml; charset="utf-8"',
      SOAPACTION: `"${ST}#${action}"`,
    },
    body: soapEnvelope(action, params),
  });
  if (!res.ok) throw new Error(`upnp ${action} -> ${res.status}`);
  return res.text();
}

function discoverViaSSDP(timeoutMs = 1500) {
  return new Promise((resolve) => {
    const sock = dgram.createSocket('udp4');
    const found = new Set();
    const msg = Buffer.from(
      `M-SEARCH * HTTP/1.1\r\nHOST: ${SSDP_ADDR}:${SSDP_PORT}\r\n` +
        `MAN: "ssdp:discover"\r\nMX: 1\r\nST: ${ST}\r\n\r\n`
    );
    sock.on('message', (buf) => {
      const txt = buf.toString();
      const m = txt.match(/LOCATION:\s*(\S+)/i);
      if (m) found.add(m[1]);
    });
    sock.bind(0, () => {
      sock.send(msg, 0, msg.length, SSDP_PORT, SSDP_ADDR);
      setTimeout(() => {
        sock.close();
        resolve([...found]);
      }, timeoutMs);
    });
  });
}

export const upnp = {
  async resolveControlUrl() {
    if (process.env.UPNP_RENDERER_URL) return process.env.UPNP_RENDERER_URL;
    const locations = await discoverViaSSDP();
    return locations[0] || null;
  },

  async play(streamUrl, { title = 'Claudio', artist = '' } = {}) {
    const url = await this.resolveControlUrl();
    if (!url) {
      console.warn('[upnp] no renderer found, skipping push');
      return false;
    }

    const didl = `<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"><item id="0" parentID="-1" restricted="1"><dc:title>${escapeXml(title)}</dc:title><dc:creator>${escapeXml(artist)}</dc:creator><upnp:class>object.item.audioItem.musicTrack</upnp:class><res protocolInfo="http-get:*:audio/mpeg:*">${escapeXml(streamUrl)}</res></item></DIDL-Lite>`;

    try {
      await soap(url, 'SetAVTransportURI', {
        InstanceID: 0,
        CurrentURI: streamUrl,
        CurrentURIMetaData: didl,
      });
      await soap(url, 'Play', { InstanceID: 0, Speed: 1 });
      return true;
    } catch (err) {
      console.warn('[upnp] push failed:', err.message);
      return false;
    }
  },

  async pause() {
    const url = await this.resolveControlUrl();
    if (!url) return false;
    try {
      await soap(url, 'Pause', { InstanceID: 0 });
      return true;
    } catch {
      return false;
    }
  },

  async resume() {
    const url = await this.resolveControlUrl();
    if (!url) return false;
    try {
      await soap(url, 'Play', { InstanceID: 0, Speed: 1 });
      return true;
    } catch {
      return false;
    }
  },
};
