/* Alai's root-scoped, network-only service worker.
   The fetch handler enables Chromium's in-app install prompt while keeping
   every Streamlit request live and avoiding stale cached app content. */
self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET" || new URL(request.url).origin !== self.location.origin) {
    return;
  }

  event.respondWith(fetch(request));
});
