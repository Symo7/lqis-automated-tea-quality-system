const CACHE_NAME = 'lqis-shell-v4';
const OFFLINE_URL = '/offline/';
const STATIC_ASSETS = [
  '/',
  OFFLINE_URL,
  '/static/css/main.css',
  '/static/js/theme.js',
  '/static/js/offline_queue.js',
  '/static/images/icons/icon.svg',
  '/static/images/icons/icon-maskable.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const accept = req.headers.get('accept') || '';

  if (accept.includes('text/html')) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
          return res;
        })
        .catch(async () => (await caches.match(req)) || (await caches.match(OFFLINE_URL)))
    );
    return;
  }

  event.respondWith(caches.match(req).then((cached) => cached || fetch(req)));
});

self.addEventListener('sync', (event) => {
  if (event.tag === 'lqis-sync') {
    event.waitUntil(
      self.clients.matchAll({ includeUncontrolled: true }).then((clients) => {
        clients.forEach((client) => client.postMessage({ type: 'TRIGGER_SYNC' }));
      })
    );
  }
});
