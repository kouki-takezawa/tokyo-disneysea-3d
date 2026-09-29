// Offline cache: the 3D models (about 20 MB) are fetched once and kept. Same-origin files are answered from the cache and
// refreshed in the background (stale-while-revalidate); the 3D library from the CDN is cache-first.
const CACHE = "tds3d-v1";
const CDN = ["https://cdn.jsdelivr.net/", "https://fonts.googleapis.com/", "https://fonts.gstatic.com/"];
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || req.headers.has("range")) return;
  const url = new URL(req.url), same = url.origin === location.origin, cdn = CDN.some(p => req.url.startsWith(p));
  if (!same && !cdn) return;
  e.respondWith(caches.open(CACHE).then(async cache => {
    const hit = await cache.match(req);
    const net = fetch(req).then(res => { if (res.ok || res.type === "opaque") cache.put(req, res.clone()).catch(() => {}); return res; });
    if (hit) { if (same) net.catch(() => {}); return hit; }
    return net;
  }));
});
