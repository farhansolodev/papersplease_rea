// The service worker: keeps every file of one build in the browser's Cache
// Storage and answers the page from it, so a later visit (even offline)
// starts without the network. The build script fills in the build code
// below (computed from the build's files), so a new build changes this
// file, which is what makes the browser install the new worker.
//
// One worker serves one build only: the page, the files it names and
// files.json all come from the same cache, so they always agree. A new
// worker downloads its build in the background (copying unchanged
// fingerprinted files from the old cache instead of fetching them) and
// starts serving on the next visit, once no tab of the old one is open.

const BUILD = '__BUILD__';
const CACHE = 'pp-' + BUILD;

self.addEventListener('install', (event) => {
  event.waitUntil(storeBuild());
});

async function storeBuild() {
  const res = await fetch('files.json', { cache: 'no-store' });
  if (!res.ok) throw new Error('files.json: ' + res.status);
  const manifest = await res.json();
  if (manifest.build !== BUILD) throw new Error('files.json is from another build');

  const cache = await caches.open(CACHE);
  const older = [];
  for (const name of await caches.keys()) {
    if (name.startsWith('pp-') && name !== CACHE) older.push(await caches.open(name));
  }
  const fingerprinted = new Set(manifest.fingerprinted);

  for (const path of manifest.files) {
    let response = null;
    if (fingerprinted.has(path)) {
      // The name holds a fingerprint of the content: the same name is the
      // same bytes, so a copy kept by an older build can be reused.
      for (const old of older) {
        response = await old.match(path);
        if (response) break;
      }
    }
    if (!response) {
      response = await fetch(path, { cache: fingerprinted.has(path) ? 'default' : 'no-store' });
      if (!response.ok) throw new Error(path + ': ' + response.status);
    }
    await cache.put(path, response);
  }
}

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (name.startsWith('pp-') && name !== CACHE) await caches.delete(name);
    }
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  const path = url.pathname.endsWith('/') ? url.pathname + 'index.html' : url.pathname;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const kept = await cache.match(new URL(path, self.location.origin), { ignoreSearch: true });
    return kept || fetch(request);
  })());
});
