// Milestone 0, 1a, 1b, 2, 3a and 3b check: drives a real browser (headless Edge or
// Chrome, with a throwaway profile in build/) against the local server and
// reports (every page opens on the start screen; the check clicks its button
// with a real mouse click, as a player would):
//   1. the picture's size and place on the canvas, from the canvas pixels,
//      at a whole-number zoom and with the start screen's "fill the window";
//   2. exact pixel values of the test card (grey 128, ramp step, red);
//   3. whether the service worker installed, and what it stored;
//   4. the font pages (milestone 1a): the whole canvas compared byte for byte
//      with the Python reference's page, for several pages, and the arrow
//      keys changing the page (needs extracted/previews/m1, made by
//      scripts/reference/fontpage.py; skipped without it);
//   4a. the title screen (milestone 1b, alive since 3a): it differs from the
//      Python reference's still while rising; after a key skips the rise the
//      whole canvas is byte for byte the reference's; the mouse over STORY
//      draws the hand cursor, a press shows STORY pressed and plays
//      button-down, the release plays button-up; all with the frame counter
//      (?fps) shown over the page (needs extracted/previews/m1b,
//      made by scripts/reference/titlescreen.py; skipped without it);
//   4b. that F5, F12, Ctrl+R and the right-click menu are not blocked
//      (defaultPrevented stays false on events sent to the canvas);
//   4c. sound (milestone 2): on the title, Theme plays, is downloaded once by
//      the service worker and is then in Cache Storage; the sound test page
//      gets all 108 effects, three of them compared sample for sample with
//      extracted/audio (skipped without it); a looping effect plays and
//      stops; a volume key gives the setting squared as the gain;
//   4d. screen changes (milestone 3b): the title's settings button fades to
//      black and opens the settings screen, compared with the Python
//      reference (extracted/previews/m3b, made by
//      scripts/reference/settingsscreen.py; skipped without it), Theme
//      playing on; Music minus kept in the page's storage and heard; the
//      Fullscreen box following the window; Escape back to the title; the
//      volume kept after a reload;
//   5. whether the page still starts with the network switched off, showing
//      the same font page, and the title's Theme plays from the cache.
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
const SETTINGS_REFERENCE = path.join(ROOT, 'extracted', 'previews', 'm3b', 'settings_a.rgba');
const AUDIO = path.join(ROOT, 'extracted', 'audio');
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

async function key(code, keyCode, name = code) {
  for (const type of ['rawKeyDown', 'keyUp']) {
    await send('Input.dispatchKeyEvent', { type, key: name, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
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

// Waits for the start screen's button, clicks it with the mouse (a real
// click, which is what lets the page play sound), then waits for the game.
async function start(what) {
  // The start screen is hidden once a page has started, so this waits for
  // the new page rather than the one being left.
  await waitFor(`(() => { const b = document.getElementById('go');
    return !!b && !b.disabled && !document.getElementById('start').hidden; })()`, 'the start button: ' + what);
  const r = await evaluate(`(() => { const b = document.getElementById('go').getBoundingClientRect(); return [b.x + b.width / 2, b.y + b.height / 2]; })()`);
  for (const type of ['mousePressed', 'mouseReleased']) {
    await send('Input.dispatchMouseEvent', { type, x: r[0], y: r[1], button: 'left', clickCount: 1 });
  }
  await waitFor('!!window.ppBuild', what);
}

// The title's song: its position in seconds, or null while it is not playing.
const THEME_AT = `(() => { const p = window.ppAudio; if (!p) return null;
  for (const [id, s] of p.playing) if (s.filename === 'Theme.ogg') return p.position(id); return null; })()`;

// Waits until Theme has played for more than a second.
async function expectTheme(what) {
  await waitFor(`(${THEME_AT}) > 1`, 'Theme to play: ' + what, 30000);
  console.log(`   Theme plays (${what}), at ${(await evaluate(THEME_AT)).toFixed(2)} s`);
}

// A WAV file's samples as the browser holds them (sample / 32768), per channel.
function wavChannels(file) {
  const b = readFileSync(file);
  const channels = b.readUInt16LE(22);
  const frames = (b.length - 44) / 2 / channels;
  const out = Array.from({ length: channels }, () => new Float32Array(frames));
  for (let i = 0; i < frames; i++) {
    for (let c = 0; c < channels; c++) out[c][i] = b.readInt16LE(44 + 2 * (i * channels + c)) / 32768;
  }
  return out;
}

// The bytes of the canvas (at 570 x 320) that differ from a reference
// picture, counted from row `fromRow` down, and the box around them.
async function differences(want, fromRow = 0) {
  const r = await evaluate(READ, 40000);
  if (r.W !== 570 || r.H !== 320) throw new Error(`canvas is ${r.W} x ${r.H}, not 570 x 320`);
  const got = Buffer.from(r.data, 'base64');
  let n = 0;
  const box = [570, 320, -1, -1];
  for (let j = fromRow * 570 * 4; j < got.length; j++) {
    if (got[j] === want[j]) continue;
    n++;
    const p = j >> 2, x = p % 570, y = Math.floor(p / 570);
    box[0] = Math.min(box[0], x); box[1] = Math.min(box[1], y);
    box[2] = Math.max(box[2], x); box[3] = Math.max(box[3], y);
  }
  return { n, box };
}

const within = (box, r) => box[0] >= r[0] && box[1] >= r[1] && box[2] < r[0] + r[2] && box[3] < r[1] + r[3];

// Milestone 3a on the title (docs/milestone-3.md): the title rises, a key
// skips the rise, then the screen at rest is the 1b still; the game's own
// cursor; a button's pressed look and its two sounds. The logo bobs with the
// music, so the cursor and button checks look only below row 230 (the
// buttons are at 236 and below).
async function titleAlive() {
  const want = readFileSync(TITLE_REFERENCE);
  await evaluate(`(() => { window.ppStarts = []; const p = window.ppAudio, s = p.start.bind(p);
    p.start = (...a) => { window.ppStarts.push(a[2]); return s(...a); }; return 1; })()`);
  await waitFor(`(${THEME_AT}) > 0.5`, 'Theme to start', 30000);
  const rising = await differences(want);
  console.log(`   rising: ${rising.n} bytes differ from the title at rest, Theme at ${(await evaluate(THEME_AT)).toFixed(2)} s`);
  if (rising.n === 0) throw new Error('the title is not rising');
  // A key skips the rise; the logo is up 40% of each bar (about 1 s), so the
  // still shows within a few seconds, long before the rise would end (23.6 s).
  await key('Space', 32, ' ');
  const t0 = Date.now();
  for (;;) {
    if ((await differences(want)).n === 0) break;
    if (Date.now() - t0 > 8000) throw new Error('the key did not skip the rise (no still within 8 s)');
    await sleep(100);
  }
  console.log(`   a key skipped the rise: identical to the reference ${((Date.now() - t0) / 1000).toFixed(1)} s later, Theme at ${(await evaluate(THEME_AT)).toFixed(2)} s`);

  // STORY: 129 x 19 at (220, 236). The hand's picture sits at (-6, -2).
  const story = [220, 236, 129, 19];
  const [mx, my] = [284, 245];
  const hand = [mx - 6, my - 2, 19, 26];
  const mouse = (type) => send('Input.dispatchMouseEvent', { type, x: mx, y: my, button: 'left', clickCount: 1 });
  const settle = async (test, what) => {
    for (let i = 0; i < 40; i++) { const d = await differences(want, 230); if (test(d)) return d; await sleep(100); }
    throw new Error(what);
  };
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: mx, y: my });
  const over = await settle((d) => d.n > 0 && within(d.box, hand), 'no hand cursor over STORY');
  console.log(`   the hand cursor over STORY: ${over.n} bytes differ, all inside the hand's picture`, JSON.stringify(over.box));
  await mouse('mousePressed');
  const pressed = await settle((d) => d.n > over.n * 2 && d.box[0] <= story[0] + 2 && d.box[2] >= story[0] + story[2] - 3,
    'STORY does not show pressed');
  const union = [story[0], story[1], story[2], hand[1] + hand[3] - story[1]];
  if (!within(pressed.box, union)) throw new Error('pressing changed pixels outside STORY and the cursor');
  console.log(`   STORY pressed: ${pressed.n} bytes differ, inside the button and the cursor`, JSON.stringify(pressed.box));
  await mouse('mouseReleased');
  await settle((d) => d.n === over.n && within(d.box, hand), 'STORY does not come back up after the click');
  await waitFor(`window.ppStarts.includes('button-up.wav')`, 'the click sound', 5000);
  const starts = await evaluate('window.ppStarts');
  console.log('   sounds started:', JSON.stringify(starts));
  const down = starts.indexOf('button-down.wav'), up = starts.indexOf('button-up.wav');
  if (down < 0 || up < down) throw new Error('button-down then button-up were not played');
}

// Milestone 3b (docs/milestone-3.md): from the title at rest, the settings
// button fades to black and opens the settings screen (identical to the
// Python reference but for the cursor) with Theme playing on; Music minus
// sets the setting to 0.9 (kept in the page's storage, music gain 0.81); the
// Fullscreen box follows what the browser allows; Escape presses DONE and
// fades back to a title that does not rise; after a reload the volume is
// still 0.9. The mouse is moved with real mouse events.
async function settingsScreen() {
  const wantSettings = readFileSync(SETTINGS_REFERENCE);
  const wantTitle = readFileSync(TITLE_REFERENCE);
  const THEME_ID = `(() => { for (const [id, s] of window.ppAudio.playing) if (s.filename === 'Theme.ogg') return id; return null; })()`;
  const themeBefore = await evaluate(THEME_ID);
  const click = async (x, y) => {
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
    await sleep(100);
    for (const type of ['mousePressed', 'mouseReleased']) {
      await send('Input.dispatchMouseEvent', { type, x, y, button: 'left', clickCount: 1 });
      await sleep(100);
    }
  };
  // The arrow's picture (19 x 26) sits at (-1, -1) from the mouse.
  const arrowAt = (x, y) => [x - 1, y - 1, 19, 26];
  // A hidden headless page is drawn about once a second and each drawing
  // runs at most 0.1 s of game time, so the game's 1.2 s screen change can
  // take 15 s or more here: the waits are long.
  const settleOn = async (want, cursor, what, ms = 40000) => {
    const t0 = Date.now();
    for (;;) {
      const d = await differences(want);
      if (d.n === 0 || within(d.box, cursor)) return { d, s: (Date.now() - t0) / 1000 };
      if (Date.now() - t0 > ms) throw new Error(`${what} (last: ${d.n} bytes differ in ${JSON.stringify(d.box)})`);
      await sleep(100);
    }
  };

  // The settings button, bottom left: 29 x 29 at (10, 281).
  await click(24, 295);
  const t0 = Date.now();
  for (;;) {
    const r = await evaluate(READ, 40000);
    const got = Buffer.from(r.data, 'base64');
    let lit = 0;
    for (let j = 0; j < 270 * 570 * 4; j += 4) if (got[j] || got[j + 1] || got[j + 2]) lit++;
    if (lit === 0) break;
    if (Date.now() - t0 > 15000) throw new Error('no black screen within 15 s of the click');
  }
  console.log(`   the settings button: the screen is black ${((Date.now() - t0) / 1000).toFixed(2)} s after the click`);
  const opened = await settleOn(wantSettings, arrowAt(24, 295), 'the settings screen did not appear');
  console.log(`   the settings screen: identical to the reference but for the cursor, ${opened.s.toFixed(1)} s after the black screen`);
  const themeAfter = await evaluate(THEME_ID);
  console.log(`   Theme plays on: play id ${themeBefore} before, ${themeAfter} after, at ${(await evaluate(THEME_AT)).toFixed(2)} s`);
  if (themeAfter !== themeBefore) throw new Error('Theme was started again');

  // Music minus: 15 x 15 at (358, 198).
  await click(365, 205);
  await waitFor(`JSON.parse(localStorage.getItem('pp.settings') || '{}').musicVolume === 0.9`, 'music 0.9 kept by the page', 5000);
  await waitFor('Math.abs(window.ppAudio.groupVolume[1] - 0.81) < 1e-6', 'the music gain 0.81', 5000);
  console.log('   Music minus: kept as', JSON.stringify(JSON.parse(await evaluate(`localStorage.getItem('pp.settings')`))),
    '; music gain', await evaluate('window.ppAudio.groupVolume[1]'));

  // The Fullscreen box at (358, 122): whatever the browser does, the box and
  // the kept setting end up agreeing with the window.
  for (const turn of ['on', 'off']) {
    await click(365, 129);
    await sleep(4000);
    const fs = await evaluate(`({ window: !!document.fullscreenElement, kept: JSON.parse(localStorage.getItem('pp.settings')).fullscreen })`);
    console.log(`   the Fullscreen box clicked (${turn}): window full screen ${fs.window}, kept ${fs.kept}`);
    if (fs.window !== fs.kept) throw new Error('the Fullscreen setting does not follow the window');
    if (!fs.window) break;
  }

  // Escape presses DONE: back to a title at rest (no rise) within seconds.
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 500, y: 200 });
  await key('Escape', 27, 'Escape');
  const back = await settleOn(wantTitle, arrowAt(500, 200), 'no title at rest after Escape');
  console.log(`   Escape: the title at rest, ${back.s.toFixed(1)} s later (a second title does not rise)`);

  // Kept after a reload.
  await send('Page.reload');
  await start('the title after a reload');
  await waitFor('Math.abs(window.ppAudio.groupVolume[1] - 0.81) < 1e-6', 'the music gain 0.81 after a reload', 10000);
  console.log('   after a reload: music setting', await evaluate('window.ppConfig.settings.musicVolume'), ', music gain', await evaluate('window.ppAudio.groupVolume[1]'));
  await evaluate(`localStorage.removeItem('pp.settings'), 1`);
}

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
  await start('the game to start');
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

  // The start screen's "fill the window": the picture keeps its shape and
  // fills the window's width here (1400 x 900: 1400 x 786 at y 57).
  await evaluate(`localStorage.setItem('pp.settings', JSON.stringify({ stretch: true })), 1`);
  await send('Page.navigate', { url: URL + '?page=testcard' });
  await start('the test card, stretched');
  await sleep(1000);
  {
    const r = await evaluate(PIXELS, 40000);
    const ok = Math.abs(r.width - 1400) <= 1 && Math.abs(r.height - 786) <= 1 && Math.abs(r.top - 57) <= 1 && r.left <= 1;
    console.log(`   stretched 1400x900: ${r.width} x ${r.height} at (${r.left},${r.top}) expected 1400 x 786 at (0,57) ->`, ok ? 'ok' : 'WRONG');
    if (!ok) throw new Error('stretch check failed');
  }
  await evaluate(`localStorage.removeItem('pp.settings'), 1`);

  // What the server has sent so far (scripts/serve.py), to count the song's
  // downloads during the title's first visit.
  const served = async () => (await fetch(URL + '_served.json')).json();
  const servedBefore = await served();

  if (existsSync(TITLE_REFERENCE)) {
    console.log('1a. the title screen alive (milestone 3a), against the Python reference at rest');
    await send('Emulation.setDeviceMetricsOverride', { width: 570, height: 320, deviceScaleFactor: 1, mobile: false });
    // With the frame counter on: it sits over the page, so the canvas must
    // still equal the reference.
    await send('Page.navigate', { url: URL + '?fps' });
    await start('the title screen to start');
    await waitFor(`/^\\d+ fps$/.test(document.getElementById('fps').textContent)`, 'the frame counter', 10000);
    console.log(`   the frame counter (?fps) shows "${await evaluate(`document.getElementById('fps').textContent`)}"`);
    await titleAlive();
  } else {
    console.log('1a. SKIPPED: no reference title in extracted/previews/m1b');
    await send('Page.navigate', { url: URL });
    await start('the title screen to start');
  }

  console.log('1d. sound: Theme on the title, kept by the service worker');
  await expectTheme('first visit, streamed');
  const songPath = await evaluate(`fetch('files.json').then((r) => r.json()).then((f) => '/' + f.songs['Theme.ogg'])`);
  const askWorker = `new Promise((r) => {
    const answer = (e) => { if (e.data && e.data.songDownloads) { navigator.serviceWorker.removeEventListener('message', answer); r(e.data); } };
    navigator.serviceWorker.addEventListener('message', answer);
    navigator.serviceWorker.controller.postMessage('song-downloads');
  })`;
  const sent = async () => {
    const now = (await served())[songPath] || {}, then = servedBefore[songPath] || {};
    return { whole: (now['200'] || 0) - (then['200'] || 0), parts: (now['206'] || 0) - (then['206'] || 0) };
  };
  try {
    await waitFor(`caches.keys().then(async (ks) => { for (const k of ks) if (await (await caches.open(k)).match('${songPath}')) return true; return false; })`,
      'Theme in Cache Storage', 30000);
  } catch (e) {
    console.log('   the worker says:', JSON.stringify(await evaluate(askWorker)));
    console.log('   the server sent:', JSON.stringify(await sent()));
    throw e;
  }
  const counts = await sent();
  console.log(`   ${songPath} is in Cache Storage; the server sent it whole ${counts.whole} time(s), in parts ${counts.parts} time(s);`,
    'the worker says:', JSON.stringify(await evaluate(askWorker)));
  if (counts.whole !== 1) throw new Error('Theme was not downloaded whole exactly once');
  const groups = await evaluate('window.ppAudio.groupVolume');
  console.log('   category volumes (settings 1.0):', JSON.stringify(groups));
  if (groups[0] !== 1 || groups[1] !== 1) throw new Error('category volumes are not 1');

  if (existsSync(TITLE_REFERENCE) && existsSync(SETTINGS_REFERENCE)) {
    console.log('1f. screen changes and the settings screen (milestone 3b)');
    await send('Emulation.setDeviceMetricsOverride', { width: 570, height: 320, deviceScaleFactor: 1, mobile: false });
    await settingsScreen();
  } else {
    console.log('1f. SKIPPED: no reference title or settings screen in extracted/previews');
  }

  console.log('1e. the sound test page');
  await send('Emulation.setDeviceMetricsOverride', { width: 1400, height: 900, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: URL + '?page=sounds' });
  await start('the sound test page to start');
  await waitFor('window.ppAudio.clips.size === 108', 'the 108 effects', 30000);
  console.log('   108 effects handed to the sound player');
  if (existsSync(path.join(AUDIO, 'audio_index.json'))) {
    // The shortest effect of each kind: stereo 44.1 kHz, mono 44.1 kHz, mono 22.05 kHz.
    const rows = JSON.parse(readFileSync(path.join(AUDIO, 'audio_index.json'), 'utf-8')).filter((r) => r.fsb_codec === 'IMAADPCM');
    for (const [ch, rate] of [[2, 44100], [1, 44100], [1, 22050]]) {
      const r = rows.filter((x) => x.channels === ch && x.rate === rate).sort((a, b) => a.samples - b.samples)[0];
      const want = wavChannels(path.join(AUDIO, r.file));
      const got = await evaluate(`(() => { const b = window.ppAudio.clips.get('${r.path}'); const out = { rate: b.sampleRate, data: [] };
        for (let c = 0; c < b.numberOfChannels; c++) { const u = new Uint8Array(b.getChannelData(c).buffer.slice(0));
          let s = ''; for (let i = 0; i < u.length; i += 32768) s += String.fromCharCode.apply(null, u.subarray(i, i + 32768)); out.data.push(btoa(s)); }
        return out; })()`, 20000);
      let differ = got.rate === rate && got.data.length === ch ? 0 : 1;
      got.data.forEach((b64, c) => {
        const f = new Float32Array(new Uint8Array(Buffer.from(b64, 'base64')).buffer);
        if (f.length !== want[c].length) differ++;
        else for (let i = 0; i < f.length; i++) if (f[i] !== want[c][i]) differ++;
      });
      console.log(`   ${r.path} (${ch} ch, ${rate} Hz, ${r.samples} samples): ${differ ? differ + ' samples DIFFER' : 'identical to the WAV'}`);
      if (differ) throw new Error('an effect differs from the WAV');
    }
  } else {
    console.log('   SKIPPED the sample comparison: no extracted/audio');
  }
  // A click gives the canvas the keyboard focus; L plays the chosen (first)
  // effect looping, S stops everything, 1 lowers the sound setting.
  for (const type of ['mousePressed', 'mouseReleased']) {
    await send('Input.dispatchMouseEvent', { type, x: 700, y: 450, button: 'left', clickCount: 1 });
  }
  await key('KeyL', 76, 'l');
  await waitFor(`(() => { const p = window.ppAudio; const [id] = [...p.playing.keys()]; return id !== undefined && p.position(id) > 0.5; })()`,
    'a looping effect to play', 10000);
  const looping = await evaluate(`[...window.ppAudio.playing.values()].map((s) => s.filename + (s.loop ? ' (loop)' : ''))`);
  console.log('   L plays:', JSON.stringify(looping));
  await key('KeyS', 83, 's');
  await waitFor('window.ppAudio.playing.size === 0', 'S to stop it', 10000);
  console.log('   S stopped it');
  await key('Digit1', 49, '1');
  await waitFor('Math.abs(window.ppAudio.groupVolume[0] - 0.81) < 1e-9', 'the sound setting 0.9 to give 0.81', 10000);
  console.log('   key 1: sound setting 0.9, effects gain', await evaluate('window.ppAudio.groupVolume[0]'));

  const haveReference = existsSync(path.join(REFERENCE, 'pages.json'));
  if (haveReference) {
    console.log('1b. font pages against the Python reference');
    await send('Emulation.setDeviceMetricsOverride', { width: 570, height: 320, deviceScaleFactor: 1, mobile: false });
    await send('Page.navigate', { url: URL + '?page=fonts&p=4' });
    await start('the font pages to start');
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
      await start('the font pages to start');
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
  await start('the game to start again');
  console.log('   worker :', JSON.stringify(await evaluate(WORKER)));

  console.log('3. network switched off, reload');
  await send('Network.enable');
  await send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
  console.log('   page fetch of files.json while offline:',
    await evaluate(`fetch('files.json', {cache: 'no-cache'}).then((r) => 'status ' + r.status).catch((e) => 'FAILED ' + e)`));
  await send('Page.reload');
  await send('Page.bringToFront');
  await start('the game to start offline');
  if (haveReference) await expectPage(34, 'offline, from the service worker');
  else console.log('   picture:', JSON.stringify(await evaluate(PIXELS, 40000)));
  await send('Page.navigate', { url: URL });
  await start('the title to start offline');
  await expectTheme('offline, from Cache Storage');
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
