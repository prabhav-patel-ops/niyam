/* Public sample frontend only. Never caches API responses or private local data. */
'use strict';
const ROOT=new URL('./',self.location.href);
const PREFIX='niyam-review-app:'+ROOT.pathname+':';
const CACHE=PREFIX+'20261113-v1';
const SHELL=['./','index.html','deployment.js?v=review-20261113','templates.js?v=review-20261113',
 'review-catalogue.js?v=review-20261113','review.js?v=review-20261113','app.js?v=app-20261113',
 'style.css?v=app-20261113','pwa.js?v=app-20261113','manifest.webmanifest','favicon.svg',
 'icons/icon-192.png','icons/icon-512.png','icons/maskable-512.png','icons/apple-touch-icon.png'];
const ALLOWED=new Set(SHELL.map(path=>new URL(path,ROOT).pathname));
self.addEventListener('install',event=>{
 event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL.map(path=>new Request(new URL(path,ROOT),{cache:'reload'})))));
});
self.addEventListener('activate',event=>{
 event.waitUntil((async()=>{
  for(const name of await caches.keys())if(name.startsWith(PREFIX)&&name!==CACHE)await caches.delete(name);
  await self.clients.claim();
 })());
});
self.addEventListener('fetch',event=>{
 const request=event.request,url=new URL(request.url);
 if(request.method!=='GET'||url.origin!==ROOT.origin||!url.pathname.startsWith(ROOT.pathname)||url.pathname.includes('/api/'))return;
 if(request.mode==='navigate'){
  // Only the app shell has an offline fallback; unrelated pages are not cached.
  if(url.pathname!==ROOT.pathname&&url.pathname!==new URL('index.html',ROOT).pathname)return;
  event.respondWith(fetch(request).then(response=>response.ok?response:Promise.reject(Error('Unavailable')))
   .catch(()=>caches.open(CACHE).then(cache=>cache.match(new URL('./',ROOT)))));
 }else if(ALLOWED.has(url.pathname)){
  // Versioned assets remain pinned to this installed shell until the next update.
  event.respondWith(caches.open(CACHE).then(async cache=>(await cache.match(request))||fetch(request)));
 }
});
self.addEventListener('message',event=>{
 if(event.data?.type==='ACTIVATE_UPDATE')self.skipWaiting();
});
