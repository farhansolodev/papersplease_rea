"""Checks of the reference aud.py (app.aud, docs/audio-layer.md): the beat
table, the title screen's rise in seconds, song changes, the booth's
ambient loops, stopping, pausing, rooms and the ignore switch.

Usage: python -I aud_check.py <reference dir> <data dir>

The host is aud.SimHost, a stand-in that keeps time (not game code), so
the timings below are the game-side rules, not measured sound.
"""
import sys

sys.path.insert(0, sys.argv[1])
import aud  # noqa: E402

data = sys.argv[2]
problems = []
DT = 1.0 / 60.0


def expect(what, got, want, tol=1e-9):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    if not ok:
        problems.append("%s: got %r, expected %r" % (what, got, want))


# ---- the beat table ---------------------------------------------------------
print("-- MusicBeat --")
mb = aud.MusicBeat()
total_beats = sum(n for _, n in mb._segments())
total_time = sum(n * 60.0 / bpm for bpm, n in mb._segments() if bpm)
print("  entries %d, beats %d, length %.3f s" % (len(mb.measures), total_beats, total_time))
expect("entries", len(mb.measures), 16)
expect("beats", total_beats, 192)
expect("table length", round(total_time, 3), 104.786, 1e-9)
expect("beat at 0 s", mb.get_beat(0.0), 0.0)
expect("beat at 9.6 s (end of bars 1-4 at 100 bpm)", mb.get_beat(9.6), 16.0, 1e-9)
expect("beat long after the end", mb.get_beat(1000.0), 192.0)
expect("time of beat 192", mb.get_time(192.0), total_time, 1e-9)
expect("time of beat 1000", mb.get_time(1000.0), total_time, 1e-9)
worst = max(abs(mb.get_beat(mb.get_time(b / 10.0)) - b / 10.0) for b in range(0, 1921))
print("  get_beat(get_time(b)) - b, worst over 0..192 in tenths: %.2e" % worst)
if worst > 1e-9:
    problems.append("get_time is not the inverse of get_beat")
for beat, bpm in ((0.0, 100.0), (15.99, 100.0), (16.0, 102.5), (39.99, 102.5), (40.0, 105.0),
                  (176.0, 125.0), (180.0, 110.0), (188.0, 90.0), (191.9, 90.0), (192.0, 100.0)):
    expect("bpm at beat %s" % beat, mb.get_bpm(beat), bpm)
fixed = aud.MusicBeat(90.0)
expect("fixed 90 bpm: beat at 2 s", fixed.get_beat(2.0), 3.0, 1e-9)
print("  bar starts in seconds:", ", ".join("%d: %.3f" % (bar, mb.get_time((bar - 1) * 4.0))
                                            for bar, _ in aud.MEASURES))
theme_length = 103.05                       # Theme.wav, docs/audio.md (4,544,512 samples / 44,100)
print("  beat when Theme loops (%.2f s): %.2f" % (theme_length, mb.get_beat(theme_length)))

# ---- the title screen's rise (docs/screens.md, part 2) ------------------------
print("\n-- the title's rise, from the beat --")
# b = beat x 0.5 + 0.035; step k begins when b reaches k; rising while b < 20
step_times = [mb.get_time(max(0.0, (k - 0.035) / 0.5)) for k in range(21)]
end = step_times[20]
print("  rise ends at beat %.2f = %.3f s; steps start at %s"
      % ((20 - 0.035) / 0.5, end, ", ".join("%.2f" % t for t in step_times[:20])))
expect("rise end (s)", round(end, 3), 23.608, 1e-9)
print("  logo bob: one cycle per bar (4 beats) = %.2f s at 100 bpm, %.2f s at 125 bpm" % (2.4, 1.92))

# ---- songs ------------------------------------------------------------------------
print("\n-- Music: a song change --")
defs = aud.SoundDefLib(data + "/Sounds.xml")
lengths = {"Theme.ogg": 103.05, "Victory.ogg": 157.71, "Death.ogg": 92.99,
           "booth-ambient.wav": 7.0, "border-ambient.wav": 14.7, "stamp-down.wav": 0.5,
           "car-driveby.wav": 5.0}
for d in defs.defs.values():
    for f in d.files:
        lengths.setdefault(f, 1.0)


def fresh():
    host = aud.SimHost(lengths)
    speaker = aud.Speaker(host, defs)
    return host, speaker, aud.Music(speaker)


def frame(host, speaker, music, before=None):
    """One Game.update, as far as sound goes: (the screen's own update,
    which may call before()), music.update, speaker.update."""
    host.advance(DT)
    if before:
        before()
    music.update()
    speaker.update(DT)


host, speaker, music = fresh()
music.play("Theme")
theme = music.play_id
for _ in range(60):
    frame(host, speaker, music)
expect("Theme position after 60 frames", round(speaker.get_play_position(theme), 4), 1.0, 1e-3)
n_calls = len(host.log)
music.play("Theme")
expect("asking again for the song that plays makes no call", len(host.log), n_calls)
music.play(None)                            # e.g. the day screen, which sets no song
volumes, frames = [], 0
while music.play_id == theme and frames < 1000:
    frame(host, speaker, music)
    frames += 1
    v = host.volume(theme)
    if v is not None:
        volumes.append(v)
stop_frame = [i for i, entry in enumerate(host.log) if entry == ("stop", theme)]
print("  Theme fades for %d frames (volume 1 - k/240), is stopped in frame %d (%.2f s), last host volumes %s; play id now %d"
      % (len(volumes), len(volumes) + 1, (len(volumes) + 1) * DT, ["%.4f" % v for v in volumes[-3:]], music.play_id))
expect("frames with a fading host volume (k/240 > 0.99 up to k = 237)", len(volumes), 237)
if any(b >= a for a, b in zip(volumes, volumes[1:])):
    problems.append("the song's fade-out is not falling")
expect("host told to stop Theme", len(stop_frame), 1)
expect("a fade to nothing leaves no song", music.play_id, 0)

host, speaker, music = fresh()
music.play("Theme")
frame(host, speaker, music)
theme = music.play_id
music.play("Victory")
gap = None
for i in range(400):
    frame(host, speaker, music)
    if music.song_id == "Victory" and music.play_id != theme and gap is None:
        gap = i + 1
print("  Theme -> Victory: Theme stopped in frame 238, Victory starts in frame %d (%.2f s after the request)" % (gap, gap * DT))
expect("Theme -> Victory: the frame Victory starts", gap, 239)
starts = [e for e in host.log if e[0] == "start"]
expect("songs start looping at volume 1 in the music category", starts[-1][2:], (aud.MUSIC, "Victory.ogg", True, 1.0))

host, speaker, music = fresh()
music.play("Nope")                          # a song the host does not have
seen = []
for _ in range(3):
    frame(host, speaker, music)
    seen.append(music.is_playing)
print("  a song the host lacks counts as playing for", seen.count(True), "update(s)")
expect("missing song: playing after updates 1, 2, 3", seen, [True, False, False])

# ---- the booth's two ambient loops ---------------------------------------------
print("\n-- the booth's ambient loops --")
host, speaker, music = fresh()
border = speaker.play("border-ambient")
booth = speaker.play("booth-ambient")
speaker.set_volume(border, 0.0, False)      # the Booth constructor
speaker.set_volume(booth, 0.0, False)
expect("border-ambient at the host after the constructor", host.volume(border), aud.f32(0.5))
expect("booth-ambient at the host after the constructor", host.volume(booth), aud.f32(0.4))


def booth_update(outside):
    def run():
        speaker.set_volume(border, 1.0 if outside else 0.0)    # fade_to not given: fades
        speaker.set_volume(booth, 0.0 if outside else 1.0)
        speaker.set_room(None if outside else "booth")
    return run


for _ in range(60):
    frame(host, speaker, music, booth_update(True))
b60 = speaker.find(border).volume
print("  outside for 1 s: border-ambient volume %.4f (host %.4f); booth-ambient host volume %.2f, never told"
      % (b60, host.volume(border), host.volume(booth)))
expect("border volume after 60 frames: 1 - (59/60)^60", b60, 1 - (59 / 60) ** 60, 1e-12)
expect("booth-ambient keeps its stored 0.4 at the host", host.volume(booth), aud.f32(0.4))
n = 60
while speaker.find(border).volume != 1.0:
    frame(host, speaker, music, booth_update(True))
    n += 1
print("  border-ambient reaches 1 after %d frames (%.2f s)" % (n, n * DT))
expect("frames to reach the target: (59/60)^n < 0.01 first at n = 275", n, 275)
frame(host, speaker, music, booth_update(False))
print("  first frame inside: booth-ambient host volume %.4f, border %.4f" % (host.volume(booth), host.volume(border)))
expect("booth-ambient first fade step", host.volume(booth), aud.f32(0.4 * DT), 1e-7)

# ---- rooms, the ignore switch, unknown ids, pausing, stopping -----------------
print("\n-- Speaker.play rules --")
speaker.set_room("booth")
expect("car-driveby (room border) while the room is booth", speaker.play("car-driveby"), 0)
speaker.set_room(None)
expect("car-driveby with no room set", speaker.play("car-driveby") > 0, True)
speaker.set_room("border")
expect("car-driveby in its room", speaker.play("car-driveby") > 0, True)
expect("an unknown id", speaker.play("no-such-sound"), 0)

host, speaker, music = fresh()
order_plain = [speaker.play("text-reveal") and host.log[-1][3] for _ in range(6)]
host, speaker, music = fresh()
order_skip = []
for i in range(6):
    if i == 2:
        speaker.ignore_non_looping_plays_this_frame()
        expect("a one-shot while ignoring", speaker.play("text-reveal"), 0)
        expect("a loop while ignoring", speaker.play("booth-ambient") > 0, True)
        speaker.update(DT)
        expect("the switch lasts one update", speaker.ignoring, False)
    speaker.play("text-reveal")
    order_skip.append(host.log[-1][3])
print("  text-reveal recordings:", order_plain, "| with a skipped play:", order_skip)
expect("a skipped play does not advance the recording order", order_skip, order_plain)

host, speaker, music = fresh()
music.play("Theme")
stamp = speaker.play("stamp-down")
amb = speaker.play("booth-ambient")
speaker.pause_all()
expect("pause_all pauses the effects category only", host.log[-1], ("setCategoryPause", aud.EFFECT, True))
speaker.stop_all(True)                      # Game.applyScreenChange
frame(host, speaker, music)
expect("stop_all(fade) leaves the song alone", speaker.find(music.play_id).state, "PLAYING")
expect("stop_all(fade) fades an effect", speaker.find(stamp).state, "STOPPING")
host, speaker, music = fresh()
music.play("Theme")
loop = speaker.play("booth-ambient")
speaker.stop_all(False, False)              # START_AUTO_SOAK
expect("stop_all(no fade, everything) stops the song at once", ("stop", music.play_id) in host.log, True)
expect("... and the effects", ("stop", loop) in host.log, True)
host, speaker, music = fresh()
loop = speaker.play("booth-ambient")
speaker.stop(loop, True)
k = 0
while ("stop", loop) not in host.log and k < 1000:
    frame(host, speaker, music)
    k += 1
print("  a looping effect stopped with a fade (fade 1 s) is stopped after %d frames" % k)
expect("fade-out frames for a 1-second fade", k, 60)

print("\nproblems:", "none" if not problems else "")
for p in problems:
    print("  " + p)
sys.exit(1 if problems else 0)
