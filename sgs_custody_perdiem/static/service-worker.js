const CACHE_NAME = 'sgs-custody-v4.0';
const urlsToCache = [
  '/',
  '/sgs/custodio/',
  '/web/static/lib/jquery/jquery.js',
  '/web/static/lib/bootstrap/js/bootstrap.js',
  '/web/static/lib/bootstrap/css/bootstrap.css',
  '/sgs_custody_perdiem/static/manifest.json',
];

// Instalación del Service Worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
      .then(() => self.skipWaiting())
  );
});

// Activación del Service Worker
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Estrategia de caché: Network First, fallback a Cache
self.addEventListener('fetch', event => {
  const { request } = event;

  // No cachear solicitudes POST, DELETE, PUT
  if (request.method !== 'GET') {
    event.respondWith(fetch(request));
    return;
  }

  // Para solicitudes GET, intentar red primero
  event.respondWith(
    fetch(request)
      .then(response => {
        // Cachear respuestas exitosas
        if (response && response.status === 200) {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME)
            .then(cache => {
              cache.put(request, responseToCache);
            });
        }
        return response;
      })
      .catch(() => {
        // Si falla la red, usar caché
        return caches.match(request)
          .then(response => {
            return response || new Response('Offline - Contenido no disponible', {
              status: 503,
              statusText: 'Service Unavailable',
              headers: new Headers({
                'Content-Type': 'text/plain'
              })
            });
          });
      })
  );
});

// Sincronización en background para enviar datos pendientes
self.addEventListener('sync', event => {
  if (event.tag === 'sync-services') {
    event.waitUntil(
      fetch('/sgs/custodio/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })
    );
  }
});

// Push notifications
self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {};
  const options = {
    body: data.body || 'Nuevo mensaje de SGS Viáticos',
    icon: '/sgs_custody_perdiem/static/icons/icon-192x192.png',
    badge: '/sgs_custody_perdiem/static/icons/badge-72x72.png',
    tag: data.tag || 'sgs-notification',
    requireInteraction: data.requireInteraction || false,
    actions: [
      {
        action: 'open',
        title: 'Abrir'
      },
      {
        action: 'close',
        title: 'Cerrar'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'SGS Viáticos', options)
  );
});

// Manejo de clicks en notificaciones
self.addEventListener('notificationclick', event => {
  event.notification.close();

  if (event.action === 'close') {
    return;
  }

  event.waitUntil(
    clients.matchAll({ type: 'window' })
      .then(clientList => {
        for (let i = 0; i < clientList.length; i++) {
          const client = clientList[i];
          if (client.url === '/sgs/custodio/' && 'focus' in client) {
            return client.focus();
          }
        }
        if (clients.openWindow) {
          return clients.openWindow('/sgs/custodio/');
        }
      })
  );
});
