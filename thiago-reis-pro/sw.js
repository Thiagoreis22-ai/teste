// Thiago Reis PRO — cache apenas dos recursos visuais. NUNCA cachear clientes, login ou API.
// Interface HTML e dados operacionais são sempre obtidos pela rede.
const CACHE_NAME = 'thiago-reis-ui-v9';
const ASSETS = ['/gold-theme.css','/responsive.css','/brand-gold.svg','/hero-gold.svg','/tr-icon.svg','/icon-192.png','/icon-512.png','/apple-touch-icon.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => Promise.allSettled(
    ASSETS.map(path => cache.add(new Request(path, {cache:'reload'}))
  )));
  self.skipWaiting();
});
self.addEventListener('activate', event => {
 event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('thiago-reis-ui-') && key !== CACHE_NAME).map(key => caches.delete(key)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch', event => {
 if(event.request.method !== 'GET' || event.request.mode === 'navigate')return;
 const url = new URL(event.request.url);
 if(url.origin !== self.location.origin || url.pathname.startsWith('/api/'))return;
 if(!ASSETS.includes(url.pathname))return;
 event.respondWith(fetch(event.request).then(response=>{
   if(response.ok){const copy=response.clone();caches.open(CACHE_NAME).then(cache=>cache.put(event.request,copy))}
   return response;
 }).catch(()=>caches.match(event.request)));
});
