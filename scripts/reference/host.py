"""The Unity side of drawing: HostUnity, QuadBatcher and the drawer's
order (docs/screen-output.md), as the desktop game runs them.

- draw_order: the drawer's layers and visuals to the list of quads the
  host draws, in order (VisualIter, QuadIter);
- batch: QuadBatcher's split of that list into meshes and submeshes;
- TextureCache: HostUnity.getTexture and the eviction in Update;
- window_size, fullscreen_mode: applyDesktopScreenResolution;
- phantom_top_left: where HostUnity.Update puts the phantom cursor;
- covered_pixels, texel_at: the graphics card's usual pixel rule.
  NOT game code: an assumption about Direct3D 11 / OpenGL, see the doc.
- quad_pixel: what Unlit/QuadShader and its blend state make of one
  pixel (read from the shader's DirectX 11 program and pass state,
  scripts/unity/scene_dump.py); the 8-bit rounding is an assumption.
- paused_pixel: Unlit/ScreenPausedShader (no game code uses it).
- AudioHost, category_attenuation_db: HostUnity.UnityPlatformAudio, how
  a sound file name becomes a playing clip and what a category volume
  does to the mixer (docs/audio.md).
Pure Python.
"""

import math

GAME_W, GAME_H = 570, 320      # Layout.kPixelWidth / kPixelHeight on desktop
SUBPIXELS = 1                  # Layout.subpixelCount on desktop
QUADS_PER_MESH = 1024          # QuadMesh: 0x1000 corners
SUBMESH_SLOTS = 32             # QuadMesh: subMeshCount 0x20
KEEP_FRAMES = 10               # Update: destroyed when last use < frame - 10
ALPHA_THRESH = 0.001           # Quad.kAlphaThresh (Quad.make skips below it)
EMPTY_LAYER_KEY = 1000000000   # VisualIter's sort: a missing layer sorts last


def draw_order(layers):
    """layers: {layer number: [visual, ...] in the order they were added},
    each visual a list of quads (dicts with at least 'valid' and 'image').
    Returns the valid quads in the order the host draws them: layers by
    number ascending, visuals in added order, tiles in order."""
    out = []
    for number in sorted(layers):
        for visual in layers[number]:
            for quad in visual:
                if quad.get("valid", True):
                    out.append(quad)
    return out


def batch(quads):
    """QuadBatcher.Add / QuadMesh.Add for one frame. quads: the drawn list
    (each with 'image'). Returns a list of meshes; each mesh is a list of
    submeshes (image, first quad index, quad count), slot 0 included."""
    meshes = []
    mesh = None
    for q in quads:
        if mesh is None:
            mesh = {"slots": [[None, 0, 0]], "count": 0}
            meshes.append(mesh)
        if not _mesh_add(mesh, q["image"]):
            mesh = {"slots": [[None, 0, 0]], "count": 0}
            meshes.append(mesh)
            _mesh_add(mesh, q["image"])
    return [[tuple(s) for s in m["slots"]] for m in meshes]


def _mesh_add(mesh, image):
    slots = mesh["slots"]
    cur = slots[-1]
    end = cur[1] + cur[2]
    if end >= QUADS_PER_MESH:
        return False
    if cur[0] is not image:
        # A new slot starts where the last one ended; the first slot of an
        # emptied mesh has no picture, so it always stays empty.
        if len(slots) >= SUBMESH_SLOTS:
            return False
        cur = [image, end, 0]
        slots.append(cur)
    cur[2] += 1
    return True


class TextureCache:
    """HostUnity.textureCache: one texture per picture number."""

    def __init__(self):
        self.entries = {}   # guid -> [generation sent, last frame used]
        self.stats = {"added": 0, "updated": 0, "removed": 0}

    def evict(self, frame):
        """Update, before drawing: drop textures unused for > 10 frames."""
        self.stats = {"added": 0, "updated": 0, "removed": 0}
        for guid in [g for g, e in self.entries.items() if e[1] < frame - KEEP_FRAMES]:
            del self.entries[guid]
            self.stats["removed"] += 1

    def get(self, guid, generation, frame):
        """getTexture: returns 'added', 'updated' (whole picture re-sent)
        or 'kept'."""
        e = self.entries.get(guid)
        if e is None:
            self.entries[guid] = [generation, frame]
            self.stats["added"] += 1
            return "added"
        e[1] = frame
        if e[0] != generation:
            e[0] = generation
            self.stats["updated"] += 1
            return "updated"
        return "kept"


def window_size(monitor_w, monitor_h, base=(GAME_W, GAME_H)):
    """applyDesktopScreenResolution, windowed: double the base size while
    twice the size is still under two thirds of the monitor both ways
    (C# whole-number division)."""
    w, h = base
    while True:
        if (monitor_w * 2) // 3 <= w * 2 or (monitor_h * 2) // 3 <= h * 2:
            return w, h
        w, h = w * 2, h * 2


def fullscreen_mode(resolutions, force1080p=False, force720p=False, stretch=False):
    """applyDesktopScreenResolution, full screen. resolutions: Unity's list
    of (w, h, refresh), smallest first; the monitor is the last entry.
    Returns ((w, h), preferred refresh 60, crop and stretch-fill switch)."""
    native = resolutions[-1][:2]
    want = (1920, 1080) if force1080p else (1280, 720) if force720p else None
    chosen = native
    if want:
        near60 = [r for r in resolutions if r[:2] == want and abs(r[2] - 60) < 2]
        anyrate = [r for r in resolutions if r[:2] == want]
        if near60:
            chosen = near60[0][:2]
        elif anyrate:
            chosen = anyrate[0][:2]
    return chosen, 60, stretch


def phantom_top_left(gx, gy, tex_w=19, tex_h=26, w=GAME_W, h=GAME_H):
    """HostUnity.Update: the phantom cursor's place, worked back from the
    screen quad's coordinates to game pixels. The object's mesh is Unity's
    built-in 'Quad', corners at -0.5 and 0.5, so centred on its position
    (read from the scene, 2026-10-17)."""
    lx = ((tex_w * 0.5 + gx) - 1.0) / w - 0.5
    ly = 0.5 - ((tex_h * 0.5 + gy) - 1.0) / h
    cx = (lx + 0.5) * w             # centre in game pixels
    cy = h - (ly + 0.5) * h
    return cx - tex_w / 2.0, cy - tex_h / 2.0


def covered_pixels(p0, p1):
    """ASSUMPTION (graphics card, not game code): pixel i is drawn when its
    centre i + 0.5 lies in [p0, p1) (top-left rule)."""
    first = math.ceil(p0 - 0.5)
    last = math.ceil(p1 - 0.5) - 1
    return list(range(first, last + 1))


def texel_at(i, p0, p1, u0, u1, size):
    """ASSUMPTION: the texel a pixel reads with nearest filtering: the
    pixel centre mapped into the texture coordinates, rounded down, held
    inside the picture (clamped edges)."""
    u = u0 + (i + 0.5 - p0) / (p1 - p0) * (u1 - u0)
    return min(max(int(math.floor(u * size)), 0), size - 1)


def to_byte(f):
    """ASSUMPTION (graphics card): a 0..1 value stored in an 8-bit channel
    is rounded to the nearest of the 256 steps."""
    return int(math.floor(min(max(f, 0.0), 1.0) * 255.0 + 0.5))


def quad_pixel(texel, colour, under):
    """One pixel of a quad drawn into the screen picture.
    texel: the picture's (r, g, b, a) bytes; colour: the quad's colour as
    four floats; under: the screen picture's (r, g, b) bytes there.
    The fragment program: c = texel / 255 * colour; out = (c.rgb * c.a, c.a).
    The pass: Blend One OneMinusSrcAlpha, so
    new = out.rgb + under * (1 - c.a). The project is in gamma colour
    space, so no sRGB conversion is made (Unity's documentation)."""
    c = [texel[i] / 255.0 * colour[i] for i in range(4)]
    a = c[3]
    return tuple(to_byte(c[i] * a + under[i] / 255.0 * (1.0 - a)) for i in range(3))


def paused_pixel(rgb):
    """Unlit/ScreenPausedShader: grey by (0.299, 0.587, 0.114), times 0.75.
    The scene's screen material uses Unlit/ScreenShader (a plain copy), and
    no game code switches to this one."""
    y = (rgb[0] * 0.299 + rgb[1] * 0.587 + rgb[2] * 0.114) / 255.0
    return (to_byte(y * 0.75),) * 3


# ---- sound (HostUnity.UnityPlatformAudio; docs/audio.md) -------------------

AUDIO_SOURCES = 32             # the constructor adds 0x20 AudioSources
VOLUME_MIN, VOLUME_MAX = 0.0001, 1.0   # setCategoryVolume's Mathf.Clamp
MIXER_GROUPS = {"music": "Master/Music", "effects": "Master/Effects"}


def category_attenuation_db(volume):
    """setCategoryVolume: the value written to the mixer's exposed
    parameter "<group>Atten" (EffectsAtten or MusicAtten), in decibels:
    20 x log10 of the volume held to 0.0001..1. So 1 is 0 dB, 0.5 about
    -6 dB, 0 (held to 0.0001) -80 dB. As a plain gain that is the held
    volume itself."""
    v = min(max(volume, VOLUME_MIN), VOLUME_MAX)
    return 20.0 * math.log10(v)


class AudioHost:
    """UnityPlatformAudio's book-keeping. names: HostUnity.audioPaths, the
    file names the game asks for ("stamp-down.wav", "Theme.ogg"), each
    standing for the clip at the same place in audioClips."""

    def __init__(self, names):
        self.clips = {}
        for i, name in enumerate(names):   # a later repeat would win (none)
            self.clips[name] = i
        self.free = AUDIO_SOURCES
        self.playing = {}                   # play id -> (clip, category, loop, volume)

    def start(self, play_id, category, filename, loop, volume):
        """start(): an unknown file name, or no free source, plays nothing
        and says nothing. Otherwise a free source gets the clip, volume,
        loop flag and the category's mixer group, and plays."""
        clip = self.clips.get(filename)
        if clip is None or self.free < 1:
            return False
        self.free -= 1
        self.playing[play_id] = (clip, category, loop, volume)
        return True

    def stop(self, play_id):
        if self.playing.pop(play_id, None) is not None:
            self.free += 1

    def update(self, finished):
        """Update(): a source that is not playing, does not loop and is at
        sample 0 is stopped and freed. finished: the play ids whose sound
        has ended (a looping sound never ends)."""
        for play_id in [p for p in self.playing if p in finished and not self.playing[p][2]]:
            self.stop(play_id)
