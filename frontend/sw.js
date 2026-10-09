/* GENOMIND — Service Worker: app shell cache-first para hardware modesto. */
"use strict";
const CACHE = "genomind-v1.1";
const SHELL = [
  "/", "/index.html", "/css/styles.css", "/js/api.js", "/js/charts.js", "/js/app.js",
  "/assets/logo.svg", "/manifest.json",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  /* API: siempre red (datos frescos científicos) */
  if (url.pathname.startsWith("/api/")) return;
  /* Shell: cache-first con revalidación en segundo plano */
  e.respondWith(
    caches.match(e.request).then((hit) => {
      const net = fetch(e.request).then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
        }
        return res;
      }).catch(() => hit);
      return hit || net;
    })
  );
});
