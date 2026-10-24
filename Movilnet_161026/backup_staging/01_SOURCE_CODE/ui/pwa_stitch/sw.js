// Service Worker - Movilnet Core PWA (Network-First Zero-Stale-Cache Architecture)
const CACHE_NAME = 'movilnet-pwa-v170-network-first';
const OFFLINE_ASSETS = [
  '/ui/assets/logos/logo_oficial.png',
  '/ui/assets/logos/boton_4gmax.png',
  '/ui/assets/logos/logo_small.png',
  '/ui/assets/logos/favicon.gif'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(OFFLINE_ASSETS).catch((err) => {
        console.warn('Cache prefetch partial warning:', err);
      });
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  // Estrategia Network-First estricta: siempre priorizar la versión en vivo del servidor
  if (event.request.method !== 'GET') {
    return;
  }
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        return networkResponse;
      })
      .catch(() => {
        return caches.match(event.request);
      })
  );
});
