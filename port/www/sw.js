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
// Songs are the exception: they are kept the first time they play (below).

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

  // Songs are not downloaded here: they are kept when first played (below).
  // A song an older build already kept is carried over.
  for (const path of Object.values(manifest.songs || {})) {
    for (const old of older) {
      const response = await old.match(path);
      if (response) { await cache.put(path, response); break; }
    }
  }
}

// Songs (docs/DESIGN.md, "Loading and caching"; docs/milestone-2.md). The
// first time a song is asked for, it is downloaded once, whole, and the data
// is split as it arrives: one copy goes on to the media player, which starts
// playing on the first part, the other is written into Cache Storage. If the
// download is cut off, the cache write fails and nothing is kept, so the
// next visit streams it again. Later requests, partial ones included, are
// answered from the cache.
const downloading = new Map();            // song path -> its cache write
const songDownloads = {};                 // song path -> network downloads (for the checks)
const songCopies = {};                    // song path -> its last copy into the cache (for the checks)
const STARTED = new Date().toISOString(); // when this run of the worker began (it is stopped when idle)

// A worker's console is not the page's: problems are also sent to every
// open page, whose loader shows them in its console.
async function report(text) {
  console.warn(text);
  for (const client of await self.clients.matchAll()) client.postMessage({ swLog: text });
}

async function answerSong(event, path) {
  const cache = await caches.open(CACHE);
  const key = new URL(path, self.location.origin).href;
  const kept = await cache.match(key);
  if (kept) return partOf(kept, event.request.headers.get('Range'));
  // Already downloading: fetch just the part this request asks for (usually
  // a small one), rather than download the whole song twice. The answer is
  // re-made here like the first one: Chrome refuses to play a file whose
  // parts come partly from the worker and partly straight from the network
  // ("no supported source", seen in the check on 2026-10-29).
  if (downloading.has(path)) {
    const range = event.request.headers.get('Range');
    const part = await fetch(key, { cache: 'no-store', headers: range ? { Range: range } : {} });
    return new Response(part.body, { status: part.status, statusText: part.statusText, headers: part.headers });
  }
  const response = await fetch(key, { cache: 'no-store' });
  songDownloads[path] = (songDownloads[path] || 0) + 1;
  if (!response.ok || !response.body) return response;
  const [toPlayer, toCache] = response.body.tee();
  const headers = new Headers(response.headers);
  // How far the copy for the cache has got (for the checks).
  const seen = songCopies[path] = { bytes: 0, size: Number(headers.get('Content-Length')) || 0, state: 'copying' };
  const counted = toCache.pipeThrough(new TransformStream({
    transform(chunk, out) { seen.bytes += chunk.byteLength; out.enqueue(chunk); },
  }));
  const write = cache.put(key, new Response(counted, { status: 200, headers }))
    .then(() => { seen.state = 'kept'; }, (e) => { seen.state = 'failed'; throw e; })
    .catch((e) => report(`song not kept: ${path}: ${e}`))
    .finally(() => downloading.delete(path));
  downloading.set(path, write);
  event.waitUntil(write);
  return new Response(toPlayer, { status: 200, headers });
}

// A kept file, or the part of it a Range header asks for ("bytes=a-b",
// "bytes=a-" or "bytes=-n").
async function partOf(kept, range) {
  if (!range) return kept;
  const m = /^bytes=(\d*)-(\d*)$/.exec(range.trim());
  const data = await kept.arrayBuffer();
  const size = data.byteLength;
  let start, end;
  if (!m || (m[1] === '' && m[2] === '')) start = size;
  else if (m[1] === '') { start = Math.max(0, size - Number(m[2])); end = size - 1; }
  else { start = Number(m[1]); end = m[2] === '' ? size - 1 : Math.min(Number(m[2]), size - 1); }
  if (start >= size || start > end) {
    return new Response(null, { status: 416, headers: { 'Content-Range': `bytes */${size}` } });
  }
  return new Response(data.slice(start, end + 1), {
    status: 206,
    headers: {
      'Content-Type': kept.headers.get('Content-Type') || 'application/octet-stream',
      'Content-Length': String(end - start + 1),
      'Content-Range': `bytes ${start}-${end}/${size}`,
      'Accept-Ranges': 'bytes',
    },
  });
}

// For the checks (scripts/checks/web_offline_check.mjs): how often each song
// was downloaded by this worker.
self.addEventListener('message', (event) => {
  if (event.data === 'song-downloads') event.source.postMessage({ songDownloads, songCopies, workerStarted: STARTED });
});

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
  const answer = path.startsWith('/songs/') ? answerSong(event, path) : (async () => {
    const cache = await caches.open(CACHE);
    const kept = await cache.match(new URL(path, self.location.origin), { ignoreSearch: true });
    return kept || fetch(request);
  })();
  event.respondWith(answer.catch((e) => {
    report(`could not answer ${path}: ${e}`);
    throw e;
  }));
});
