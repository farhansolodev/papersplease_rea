// Milestone 0, 1a and 1b check: drives a real browser (headless Edge or Chrome,
// with a throwaway profile in build/) against the local server and reports:
//   1. the picture's size and place on the canvas, from the canvas pixels;
//   2. exact pixel values of the test card (grey 128, ramp step, red);
//   3. whether the service worker installed, and what it stored;
//   4. the font pages (milestone 1a): the whole canvas compared byte for byte
//      with the Python reference's page, for several pages, and the arrow
//      keys changing the page (needs extracted/previews/m1, made by
//      scripts/reference/fontpage.py; skipped without it);
//   4a. the title screen (milestone 1b): the whole canvas compared byte for
//      byte with the Python reference's (needs extracted/previews/m1b, made
//      by scripts/reference/titlescreen.py; skipped without it);
//   4b. that F5, F12, Ctrl+R and the right-click menu are not blocked
//      (defaultPrevented stays false on events sent to the canvas);
//   5. whether the page still starts with the network switched off, showing
//      the same font page.
//
//   node scripts/checks/web_offline_check.mjs [port]     (server running)
//
// Nothing is changed outside build/_browser_profile, which is deleted.

import { spawn, spawnSync } from 'node:child_process';
import { existsSync, rmSync, mkdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const PORT = process.argv[2] || '8080';
const URL = `http://localhost:${PORT}/`;
const DEBUG_PORT = 9333;
const REFERENCE = path.join(ROOT, 'extracted', 'previews', 'm1');
const TITLE_REFERENCE = path.join(ROOT, 'extracted', 'previews', 'm1b', 'title.rgba');
const PROFILE = path.join(ROOT, 'build', '_browser_profile');
const BROWSERS = [
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
];
const exe = BROWSERS.find(existsSync);
if (!exe) { console.error('no Edge or Chrome found'); process.exit(1); }

// Stop the whole check if something hangs.
setTimeout(() => { console.log('   RESULT: FAILED - hung for 5 minutes'); stopProfileBrowsers(); process.exit(2); }, 300000).unref?.();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Stops every browser process that uses the throwaway profile (the
// browser starts helper processes that outlive it and lock the folder).
function stopProfileBrowsers() {
  spawnSync('powershell', ['-NoProfile', '-Command',
    "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*_browser_profile*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"]);
}
stopProfileBrowsers();
rmSync(PROFILE, { recursive: true, force: true, maxRetries: 10, retryDelay: 500 });
mkdirSync(PROFILE, { recursive: true });

const browser = spawn(exe, [
  '--headless=new', `--remote-debugging-port=${DEBUG_PORT}`, `--user-data-dir=${PROFILE}`,
  '--no-first-run', '--no-default-browser-check', '--window-size=1400,900',
  '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist',
  'about:blank',
], { stdio: 'ignore' });

async function connect() {
  for (let i = 0; i < 50; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${DEBUG_PORT}/json`)).json();
      const page = list.find((t) => t.type === 'page');
      if (page) return page.webSocketDebuggerUrl;
    } catch { /* not up yet */ }
    await sleep(200);
  }
  throw new Error('browser did not start');
}

let id = 0;
const waiting = new Map();
let ws;
function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const n = ++id;
    waiting.set(n, { resolve, reject });
    ws.send(JSON.stringify({ id: n, method, params }));
  });
}
async function evaluate(expression, ms = 8000) {
  const r = await Promise.race([
    send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }),
    sleep(ms).then(() => { throw new Error(`page did not answer in ${ms / 1000} s`); }),
  ]);
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
  return r.result.value;
}

// Runs in the page: waits for the canvas, then reads pixels from the
// graphics context right after a frame (the only moment they are valid).
const PIXELS = `(async () => {
  const c = document.getElementById('game');
  const gl = c.getContext('webgl2');
  const frame = () => new Promise((r) => requestAnimationFrame(() => r()));
  await frame(); await frame();
  const px = (x, y) => { const b = new Uint8Array(4); gl.readPixels(x, c.height - 1 - y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, b); return Array.from(b); };
  const W = c.width, H = c.height, cx = (W >> 1) + 1, cy = (H >> 1) + 1;
  let top = -1, bot = -1, left = -1, right = -1;
  for (let y = 0; y < H; y++) if (px(cx, y)[0] > 200) { if (top < 0) top = y; bot = y; }
  for (let x = 0; x < W; x++) if (px(x, cy)[0] > 200) { if (left < 0) left = x; right = x; }
  const zoom = (right - left + 1) / 570;
  const at = (gx, gy) => px(left + Math.round(gx * zoom), top + Math.round(gy * zoom));
  return { dpr: devicePixelRatio, canvas: [W, H], left, top, width: right - left + 1, height: bot - top + 1, zoom,
           grey128: at(30, 100), ramp7: at(20 + 24 * 7 + 5, 55), red: at(30, 75), build: window.ppBuild };
})()`;

// The whole canvas as 570 x 320 x 4 bytes (rows top to bottom), base64.
const READ = `(async () => {
  const c = document.getElementById('game');
  const gl = c.getContext('webgl2');
  const frame = () => new Promise((r) => requestAnimationFrame(() => r()));
  await frame(); await frame();
  const W = c.width, H = c.height;
  const raw = new Uint8Array(W * H * 4);
  gl.readPixels(0, 0, W, H, gl.RGBA, gl.UNSIGNED_BYTE, raw);
  const out = new Uint8Array(W * H * 4);
  for (let y = 0; y < H; y++) out.set(raw.subarray((H - 1 - y) * W * 4, (H - y) * W * 4), y * W * 4);
  let s = '';
  for (let i = 0; i < out.length; i += 32768) s += String.fromCharCode.apply(null, out.subarray(i, i + 32768));
  return { W, H, data: btoa(s) };
})()`;

// Waits until the canvas (at 570 x 320) equals the reference's page n.
async function expectPage(n, what) {
  await expectPicture(path.join(REFERENCE, `page_${String(n).padStart(3, '0')}.rgba`), `page ${n}`, what);
}

// Waits until the canvas (at 570 x 320) equals a reference picture.
async function expectPicture(file, name, what) {
  const want = readFileSync(file);
  let last = 'nothing read';
  for (let i = 0; i < 60; i++) {
    const r = await evaluate(READ, 40000);
    if (r.W === 570 && r.H === 320) {
      const got = Buffer.from(r.data, 'base64');
      const differ = got.reduce((k, b, j) => k + (b !== want[j] ? 1 : 0), 0);
      if (differ === 0) { console.log(`   ${name}: identical to the reference (${what})`); return; }
      last = `${differ} bytes differ`;
    } else last = `canvas is ${r.W} x ${r.H}, not 570 x 320`;
    await sleep(500);
  }
  throw new Error(`${name} (${what}): ${last}`);
}

async function key(code, keyCode) {
  for (const type of ['rawKeyDown', 'keyUp']) {
    await send('Input.dispatchKeyEvent', { type, key: code, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
  }
}

const WORKER = `(async () => {
  const regs = await navigator.serviceWorker.getRegistrations();
  const out = { registrations: regs.length, active: regs.some((r) => r.active), controlled: !!navigator.serviceWorker.controller, caches: {} };
  for (const k of await caches.keys()) {
    out.caches[k] = (await (await caches.open(k)).keys()).map((r) => new URL(r.url).pathname);
  }
  return out;
})()`;

async function waitFor(expression, what, ms = 60000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    try { if (await evaluate(expression)) return; } catch { /* page reloading */ }
    await sleep(500);
  }
  let state = '';
  try {
    state = await evaluate(`JSON.stringify({ href: location.href, ready: document.readyState, status: (document.getElementById('status')||{}).textContent,
      controller: !!navigator.serviceWorker.controller, resources: performance.getEntriesByType('resource').map((e) => e.name.split('/').pop() + ' ' + Math.round(e.duration) + 'ms') })`);
  } catch (e) { state = 'page state unavailable: ' + e.message; }
  console.log('   page state:', state);
  throw new Error('timed out waiting for ' + what);
}

try {
  ws = new WebSocket(await connect());
  await new Promise((r) => (ws.onopen = r));
  ws.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.method === 'Runtime.exceptionThrown') console.log('   [page exception]', JSON.stringify(d.params.exceptionDetails).slice(0, 300));
    if (d.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(d.params.type)) {
      console.log('   [page ' + d.params.type + ']', d.params.args.map((a) => a.value ?? a.description).join(' ').slice(0, 300));
    }
    if (d.id && waiting.has(d.id)) {
      const w = waiting.get(d.id); waiting.delete(d.id);
      d.error ? w.reject(new Error(JSON.stringify(d.error))) : w.resolve(d.result);
    }
  };
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setFocusEmulationEnabled', { enabled: true });  // a headless page counts as focused and visible
  await send('Emulation.setDeviceMetricsOverride', { width: 1400, height: 900, deviceScaleFactor: 1, mobile: false });

  console.log('1. first visit, the milestone 0 test card', URL);
  await send('Page.navigate', { url: URL + '?page=testcard' });
  await waitFor('!!window.ppBuild', 'the game to start');
  console.log('   picture:', JSON.stringify(await evaluate(PIXELS, 40000)));
  // Window sizes and the zoom the core's fit rule gives for each.
  for (const [w, h, zoom] of [[1800, 1000, 3], [1000, 700, 1], [1200, 1500, 2], [1710, 960, 3]]) {
    await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false });
    await sleep(1500);
    const r = await evaluate(PIXELS, 40000);
    const ok = r.zoom === zoom && r.width === 570 * zoom && r.height === 320 * zoom
      && r.left === Math.floor((w - 570 * zoom) / 2) && r.top === Math.floor((h - 320 * zoom) / 2);
    console.log(`   resize ${w}x${h}: zoom ${r.zoom} at (${r.left},${r.top}) expected zoom ${zoom} ->`, ok ? 'ok' : 'WRONG');
    if (!ok) throw new Error('resize check failed');
  }
  await send('Emulation.setDeviceMetricsOverride', { width: 1400, height: 900, deviceScaleFactor: 1, mobile: false });
  await sleep(1000);
  await waitFor(`(async()=>{const r=await navigator.serviceWorker.getRegistration(); return !!(r&&r.active)})()`, 'the service worker');
  console.log('   worker :', JSON.stringify(await evaluate(WORKER)));

  if (existsSync(TITLE_REFERENCE)) {
    console.log('1a. the title screen against the Python reference');
    await send('Emulation.setDeviceMetricsOverride', { width: 570, height: 320, deviceScaleFactor: 1, mobile: false });
    await send('Page.navigate', { url: URL });
    await waitFor('!!window.ppBuild', 'the title screen to start');
    await expectPicture(TITLE_REFERENCE, 'title', 'the default page');
  } else {
    console.log('1a. SKIPPED: no reference title in extracted/previews/m1b');
  }

  const haveReference = existsSync(path.join(REFERENCE, 'pages.json'));
  if (haveReference) {
    console.log('1b. font pages against the Python reference');
    await send('Emulation.setDeviceMetricsOverride', { width: 570, height: 320, deviceScaleFactor: 1, mobile: false });
    await send('Page.navigate', { url: URL + '?page=fonts&p=4' });
    await waitFor('!!window.ppBuild', 'the font pages to start');
    await expectPage(4, 'regular');
    // A click gives the canvas the keyboard focus; then the arrow keys.
    for (const type of ['mousePressed', 'mouseReleased']) {
      await send('Input.dispatchMouseEvent', { type, x: 100, y: 100, button: 'left', clickCount: 1 });
    }
    await key('ArrowRight', 39);
    await expectPage(5, 'after ArrowRight');
    // One key at a time: two presses inside one frame count as one.
    await key('ArrowLeft', 37);
    await expectPage(4, 'after ArrowLeft');
    await key('ArrowLeft', 37);
    await expectPage(3, 'after another ArrowLeft: digits');
    for (const n of [16, 34]) {
      await send('Page.navigate', { url: URL + `?page=fonts&p=${n}` });
      await waitFor('!!window.ppBuild', 'the font pages to start');
      await expectPage(n, n < 16 ? 'text page' : 'font sheet part');
    }
  } else {
    console.log('1b. SKIPPED: no reference pages in extracted/previews/m1');
  }

  // The game must not swallow the browser's own keys (F5, F12, Ctrl+R) or
  // the right-click menu. A cancelable event is sent to the canvas; if the
  // game called preventDefault, defaultPrevented is true afterwards.
  console.log('1c. browser keys and right click are left alone');
  const swallowed = await evaluate(`(() => {
    const c = document.querySelector('#game');
    const out = {};
    const keys = [['F5', {}], ['F12', {}], ['r', { ctrlKey: true }]];
    for (const [k, extra] of keys) {
      const e = new KeyboardEvent('keydown', { key: k, code: k === 'r' ? 'KeyR' : k, bubbles: true, cancelable: true, ...extra });
      c.dispatchEvent(e);
      out[(extra.ctrlKey ? 'Ctrl+' : '') + k] = e.defaultPrevented;
    }
    const m = new MouseEvent('contextmenu', { button: 2, bubbles: true, cancelable: true });
    c.dispatchEvent(m);
    out.contextmenu = m.defaultPrevented;
    return out;
  })()`);
  console.log('   defaultPrevented:', JSON.stringify(swallowed));
  if (Object.values(swallowed).some(Boolean)) throw new Error('the game blocks a browser key or the right-click menu');

  console.log('2. reload (now controlled by the worker)');
  await send('Page.reload');
  await waitFor('!!window.ppBuild', 'the game to start again');
  console.log('   worker :', JSON.stringify(await evaluate(WORKER)));

  console.log('3. network switched off, reload');
  await send('Network.enable');
  await send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
  console.log('   page fetch of files.json while offline:',
    await evaluate(`fetch('files.json', {cache: 'no-cache'}).then((r) => 'status ' + r.status).catch((e) => 'FAILED ' + e)`));
  await send('Page.reload');
  await send('Page.bringToFront');
  await waitFor('!!window.ppBuild', 'the game to start offline');
  if (haveReference) await expectPage(34, 'offline, from the service worker');
  else console.log('   picture:', JSON.stringify(await evaluate(PIXELS, 40000)));
  console.log('   RESULT: starts offline');
} catch (e) {
  console.log('   RESULT: FAILED -', e.message);
  process.exitCode = 1;
} finally {
  try { ws && ws.close(); } catch { /* ignore */ }
  stopProfileBrowsers();
  await sleep(2000);
  try {
    rmSync(PROFILE, { recursive: true, force: true, maxRetries: 10, retryDelay: 500 });
  } catch (e) {
    console.log('   (could not delete build/_browser_profile yet:', e.code + ')');
  }
}
