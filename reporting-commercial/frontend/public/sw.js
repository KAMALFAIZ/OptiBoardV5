/*
 * OptiBoard — Service Worker PWA
 *
 * Strategies :
 *  - /api/*            : JAMAIS intercepte (donnees temps reel, auth par session)
 *  - navigations (SPA) : network-first, fallback index.html en cache, puis offline.html
 *  - /assets/*         : cache-first (fichiers Vite avec hash dans le nom = immuables)
 *  - autres statiques  : stale-while-revalidate (icones, favicon, manifest)
 *
 * SW_VERSION : bumpe a chaque release frontend (voir scripts/release/bump_version.ps1).
 * Les assets etant hashes, un vieux cache ne sert jamais un mauvais fichier ;
 * le bump sert uniquement a purger les entrees orphelines.
 */
const SW_VERSION = 'v1'
const STATIC_CACHE = `optiboard-static-${SW_VERSION}`
const PAGES_CACHE = `optiboard-pages-${SW_VERSION}`
const RUNTIME_CACHE = `optiboard-runtime-${SW_VERSION}`
const ALL_CACHES = [STATIC_CACHE, PAGES_CACHE, RUNTIME_CACHE]

const PRECACHE_URLS = [
  '/offline.html',
  '/manifest.json',
  '/favicon.svg',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/icons/icon-maskable-192.png',
  '/icons/icon-maskable-512.png',
  '/icons/apple-touch-icon.png',
]

// Limite du cache runtime pour ne pas grossir indefiniment
const RUNTIME_MAX_ENTRIES = 200

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE_URLS))
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const names = await caches.keys()
      await Promise.all(
        names
          .filter((n) => n.startsWith('optiboard-') && !ALL_CACHES.includes(n))
          .map((n) => caches.delete(n))
      )
      await self.clients.claim()
    })()
  )
})

// Le client envoie SKIP_WAITING quand l'utilisateur accepte la mise a jour
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting()
  }
})

async function trimCache(cacheName, maxEntries) {
  const cache = await caches.open(cacheName)
  const keys = await cache.keys()
  if (keys.length > maxEntries) {
    await cache.delete(keys[0])
    return trimCache(cacheName, maxEntries)
  }
}

async function networkFirstNavigation(request) {
  const cache = await caches.open(PAGES_CACHE)
  try {
    const response = await fetch(request)
    if (response && response.ok) {
      // Toujours garder la derniere index.html valide pour le mode hors-ligne
      cache.put('/', response.clone())
    }
    return response
  } catch (_) {
    const cachedIndex = await cache.match('/')
    if (cachedIndex) return cachedIndex
    const offline = await caches.match('/offline.html')
    if (offline) return offline
    return new Response('Hors ligne', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } })
  }
}

async function cacheFirst(request) {
  const cached = await caches.match(request)
  if (cached) return cached
  const response = await fetch(request)
  if (response && response.ok) {
    const cache = await caches.open(RUNTIME_CACHE)
    cache.put(request, response.clone())
    trimCache(RUNTIME_CACHE, RUNTIME_MAX_ENTRIES)
  }
  return response
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(RUNTIME_CACHE)
  const cached = await cache.match(request)
  const fetchPromise = fetch(request)
    .then((response) => {
      if (response && response.ok) {
        cache.put(request, response.clone())
        trimCache(RUNTIME_CACHE, RUNTIME_MAX_ENTRIES)
      }
      return response
    })
    .catch(() => cached)
  return cached || fetchPromise
}

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return

  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return
  // Les donnees metier et l'auth ne passent JAMAIS par le cache SW
  if (url.pathname.startsWith('/api/')) return

  if (request.mode === 'navigate') {
    event.respondWith(networkFirstNavigation(request))
    return
  }

  // Bundles Vite : nom hashe -> immuable -> cache-first
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(cacheFirst(request))
    return
  }

  // Icones, manifest, favicon, etc.
  event.respondWith(staleWhileRevalidate(request))
})
