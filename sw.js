// Field Eye offline support: the app, its starter photos and the sign-in code keep working without a connection.
const V = "field-eye-v5";
const SHELL = ["./", "./index.html", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png"];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(V).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== V).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const r = e.request;
  if (r.method !== "GET") return;
  const u = new URL(r.url);
  const same = u.origin === location.origin;
  const lib = u.hostname === "www.gstatic.com" && u.pathname.startsWith("/firebasejs/");
  const fonts = u.hostname === "fonts.googleapis.com" || u.hostname === "fonts.gstatic.com";
  if (!same && !lib && !fonts) return;
  const put = (res) => { if (res.ok || res.type === "opaque") { const cp = res.clone(); caches.open(V).then((c) => c.put(r, cp)); } return res; };
  // The page and the starter list: newest when online, saved copy when offline.
  if (r.mode === "navigate" || (same && /(\/|\.html|starter\.json)$/.test(u.pathname))) {
    e.respondWith(fetch(r).then(put).catch(() => caches.match(r).then((m) => m || caches.match("./index.html"))));
    return;
  }
  // Photos, icons, fonts and library files: saved copy first.
  e.respondWith(caches.match(r).then((m) => m || fetch(r).then(put)));
});
