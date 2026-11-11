const CACHE_NAME = 'eparoisse-shell-v2';
const APP_SHELL = '/';
const PRECACHE_URLS = [
    APP_SHELL,
    '/manifest.json',
    '/icon.svg',
    '/favicon.svg',
    '/favicon.ico',
    '/favicon.png',
    '/icon-192.png',
    '/icon-512.png',
    '/icon-maskable-512.png',
    '/apple-touch-icon.png',
];

self.addEventListener('install', (event) => {
    event.waitUntil((async () => {
        const cache = await caches.open(CACHE_NAME);
        await cache.addAll(PRECACHE_URLS);
        const response = await cache.match(APP_SHELL);
        if (response) {
            const html = await response.text();
            const assets = [...html.matchAll(/(?:src|href)=["']([^"']+\.(?:js|css))["']/g)]
                .map((match) => new URL(match[1], self.location.origin).href)
                .filter((url) => new URL(url).origin === self.location.origin);
            await Promise.allSettled(assets.map((asset) => cache.add(asset)));
        }
        await self.skipWaiting();
    })());
});

self.addEventListener('activate', (event) => {
    event.waitUntil((async () => {
        const keys = await caches.keys();
        await Promise.all(keys.filter((key) => key.startsWith('eparoisse-shell-') && key !== CACHE_NAME)
            .map((key) => caches.delete(key)));
        await self.clients.claim();
    })());
});

self.addEventListener('fetch', (event) => {
    const request = event.request;
    const url = new URL(request.url);
    if (request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/')) {
        return;
    }

    if (request.mode === 'navigate') {
        event.respondWith((async () => {
            try {
                const response = await fetch(request);
                if (response.ok) {
                    const cache = await caches.open(CACHE_NAME);
                    await cache.put(APP_SHELL, response.clone());
                }
                return response;
            } catch {
                return (await caches.match(APP_SHELL)) || Response.error();
            }
        })());
        return;
    }

    event.respondWith((async () => {
        try {
            const response = await fetch(request);
            if (response.ok) {
                const cache = await caches.open(CACHE_NAME);
                await cache.put(request, response.clone());
            }
            return response;
        } catch {
            return (await caches.match(request)) || Response.error();
        }
    })());
});
