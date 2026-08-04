/* Service Worker: app shell precache + runtime cache para datos e imágenes */
const V = 'ms102-v3';
const SHELL = ['./','./index.html','./styles.css?v=3','./app.js?v=3','./manifest.json',
  './icons/icon-192.png','./icons/icon-512.png'];

self.addEventListener('install', e=>{
  e.waitUntil(caches.open(V).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate', e=>{
  e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch', e=>{
  const req = e.request;
  if(req.method!=='GET') return;
  const url = new URL(req.url);
  // datos e imágenes: cache-first con actualización en segundo plano
  if(url.pathname.includes('/data/')){
    e.respondWith(caches.open(V).then(async c=>{
      const hit = await c.match(req);
      const net = fetch(req).then(r=>{ if(r.ok) c.put(req, r.clone()); return r; }).catch(()=>hit);
      return hit || net;
    }));
    return;
  }
  // shell: cache-first
  e.respondWith(caches.match(req).then(r=> r || fetch(req)));
});
