const CACHE_NAME = 'visiontrader-ai-cache-v3';
const ASSETS_TO_CACHE = [
  '/index.html',
  '/login.html',
  '/register.html',
  '/dashboard.html',
  '/upload.html',
  '/history.html',
  '/calendar.html',
  '/settings.html',
  '/chat.html',
  '/ask-ai.html',
  '/journal.html',
  '/result.html',
  '/backtest.html',
  '/strategy_factory.html',
  '/strategy-battle.html',
  '/academy.html',
  '/evolution.html',
  '/heatmap.html',
  '/realtime.html',
  '/service-health.html',
  '/system-health.html',
  '/api-docs.html',
  '/admin.html',
  '/css/style.css',
  '/js/api.js',
  '/manifest.json',
  '/service-worker.js',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png'
];

self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS_TO_CACHE))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => Promise.all(
      cacheNames.map(cacheName => {
        if (cacheName !== CACHE_NAME) {
          return caches.delete(cacheName);
        }
      })
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  event.respondWith(
    fetch(event.request)
      .then(networkResponse => {
        if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
          return networkResponse;
        }

        const responseClone = networkResponse.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, responseClone));
        return networkResponse;
      })
      .catch(() => {
        return caches.match(event.request).then(cachedResponse => {
          if (cachedResponse) {
            return cachedResponse;
          }
          if (event.request.mode === 'navigate') {
            return caches.match('/index.html');
          }
          return caches.match('/css/style.css');
        });
      })
  );
});
