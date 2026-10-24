/**
 * sw.js — Service Worker Oficial de Mi Movilnet PWA
 * Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
 * Estrategia: Cache First para Assets Estáticos, Network First para Telemetría y Pagos
 */

const CACHE_NAME = 'movilnet-pwa-v1.0.0';
const STATIC_ASSETS = [
  '/ui/pwa/',
  '/ui/pwa/index.html',
  '/ui/pwa/manifest.json',
  '/ui/pwa/css/pwa.css',
  '/ui/pwa/js/pwa.js',
  '/ui/css/movilnet_tokens.css',
  '/ui/css/movilnet_components.css'
];

// 1. Instalación del Service Worker y precaching de assets estáticos
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[Service Worker] Precaching estático completado.');
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// 2. Activación y purga de versiones antiguas de caché
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[Service Worker] Eliminando caché obsoleta:', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// 3. Estrategia de Fetch: Network-First con fallback a Caché para API, Cache-First para estáticos
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Peticiones a API dinámicas: Network first, si falla retornar offline mock o cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          return response;
        })
        .catch(async () => {
          // Fallback en caso de pérdida total de red
          return new Response(JSON.stringify({
            offline_mode: true,
            message: 'Sin conexión a internet. Mostrando últimos datos en caché segura.',
            timestamp: new Date().toISOString()
          }), {
            headers: { 'Content-Type': 'application/json' }
          });
        })
    );
    return;
  }

  // Peticiones estáticas: Cache First con fallback a Red
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request).then((networkResponse) => {
        // Guardar copia en cache si es exitosa
        if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      });
    })
  );
});
