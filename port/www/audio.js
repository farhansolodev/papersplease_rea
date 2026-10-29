// The sound player: the browser's version of the original's Unity host,
// HostUnity.UnityPlatformAudio (docs/audio.md, "How the host plays a sound").
// The game (through the Rust host) talks to it as the original's game side
// talks to Unity:
//
//   start(playId, category, filename, loop, volume)   category 0 effect, 1 music
//   stop(playId)
//   setVolume(playId, volume)
//   position(playId)               seconds, or -1 for an id it does not have
//   setCategoryPause(category, paused)
//   setCategoryVolume(category, volume)
//   update()                       once a frame: frees finished one-shots
//
// As in the original: at most 32 sounds at once, and a sound whose file is
// unknown, or a 33rd, is silently not played. A category's volume is held to
// 0.0001..1 and applied as 20 x log10 decibels on its mixer group, which is
// the same gain (so 0 plays at -80 dB, not silence). Nothing else is done to
// the sound: the original's mixer has no effects.
//
// Effects are decoded by the game (port/core/src/adpcm.rs) and handed over
// with addClip. Songs are played by the browser's own media player from
// their file, so a song starts while it is still downloading; the service
// worker keeps the download (port/www/sw.js).

const SOURCES = 32;
const EFFECT = 0, MUSIC = 1;

export class SoundPlayer {
  constructor(context, songs) {
    this.context = context;
    this.songs = songs;           // "Theme.ogg" -> its address
    this.clips = new Map();       // "stamp-down.wav" -> AudioBuffer
    this.playing = new Map();     // play id -> sound
    this.groups = [EFFECT, MUSIC].map(() => {
      const g = context.createGain();
      g.connect(context.destination);
      return g;
    });
    this.groupVolume = [1, 1];
    this.groupPaused = [false, false];
  }

  // samples: Int16Array, channels interleaved, as the game stores them.
  addClip(name, channels, rate, samples) {
    const frames = samples.length / channels;
    const buffer = this.context.createBuffer(channels, frames, rate);
    for (let c = 0; c < channels; c++) {
      const out = new Float32Array(frames);
      for (let i = 0, j = c; i < frames; i++, j += channels) out[i] = samples[j] / 32768;
      buffer.copyToChannel(out, c);
    }
    this.clips.set(name, buffer);
  }

  start(playId, category, filename, loop, volume) {
    const clip = this.clips.get(filename);
    const song = this.songs[filename];
    if ((!clip && !song) || this.playing.size >= SOURCES) return false;
    const gain = this.context.createGain();
    gain.gain.value = volume;
    gain.connect(this.groups[category === MUSIC ? MUSIC : EFFECT]);
    const sound = { category, filename, loop, gain, clip, element: null, node: null,
                    startedAt: 0, offset: 0, paused: false, finished: false };
    if (clip) {
      this.playBuffer(sound, 0);
    } else {
      const element = new Audio();
      element.preload = 'auto';
      element.loop = loop;
      element.src = song;
      element.addEventListener('ended', () => { sound.finished = true; });
      sound.element = element;
      sound.node = this.context.createMediaElementSource(element);
      sound.node.connect(gain);
      element.play().catch((e) => console.warn('song did not start:', filename, e));
    }
    this.playing.set(playId, sound);
    if (this.groupPaused[sound.category === MUSIC ? MUSIC : EFFECT]) this.pause(sound);
    return true;
  }

  playBuffer(sound, offset) {
    const node = this.context.createBufferSource();
    node.buffer = sound.clip;
    node.loop = sound.loop;
    node.connect(sound.gain);
    node.onended = () => { if (sound.node === node && !sound.paused) sound.finished = true; };
    node.start(0, offset);
    sound.node = node;
    sound.offset = offset;
    sound.startedAt = this.context.currentTime;
  }

  stop(playId) {
    const sound = this.playing.get(playId);
    if (!sound) return;
    this.playing.delete(playId);
    if (sound.element) {
      sound.element.pause();
      sound.element.removeAttribute('src');
      sound.element.load();
    } else if (sound.node) {
      sound.node.onended = null;
      try { sound.node.stop(); } catch { /* not started */ }
    }
    sound.node && sound.node.disconnect();
    sound.gain.disconnect();
  }

  setVolume(playId, volume) {
    const sound = this.playing.get(playId);
    if (sound) sound.gain.gain.value = volume;
  }

  position(playId) {
    const sound = this.playing.get(playId);
    if (!sound) return -1;
    if (sound.element) return sound.element.currentTime;
    return this.bufferPosition(sound);
  }

  bufferPosition(sound) {
    if (sound.paused) return sound.offset;
    const t = sound.offset + (this.context.currentTime - sound.startedAt);
    const d = sound.clip.duration;
    return sound.loop ? t % d : Math.min(t, d);
  }

  pause(sound) {
    if (sound.paused) return;
    if (sound.element) {
      sound.element.pause();
    } else {
      sound.offset = this.bufferPosition(sound);
      sound.node.onended = null;
      try { sound.node.stop(); } catch { /* not started */ }
      sound.node.disconnect();
    }
    sound.paused = true;
  }

  resume(sound) {
    if (!sound.paused) return;
    sound.paused = false;
    if (sound.element) sound.element.play().catch(() => {});
    else this.playBuffer(sound, sound.offset);
  }

  // The original keeps one pause state per source: resuming a category
  // resumes only what that category's pause paused.
  setCategoryPause(category, paused) {
    const group = category === MUSIC ? MUSIC : EFFECT;
    this.groupPaused[group] = paused;
    for (const sound of this.playing.values()) {
      if ((sound.category === MUSIC ? MUSIC : EFFECT) !== group) continue;
      paused ? this.pause(sound) : this.resume(sound);
    }
  }

  setCategoryVolume(category, volume) {
    const group = category === MUSIC ? MUSIC : EFFECT;
    const held = Math.min(1, Math.max(0.0001, volume));
    const decibels = 20 * Math.log10(held);
    this.groupVolume[group] = Math.pow(10, decibels / 20);
    this.groups[group].gain.value = this.groupVolume[group];
  }

  // A sound that is not playing, does not loop and is not paused has
  // finished: its source is freed.
  update() {
    for (const [id, sound] of this.playing) {
      if (sound.finished && !sound.loop && !sound.paused) this.stop(id);
    }
  }
}
