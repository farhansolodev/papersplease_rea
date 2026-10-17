"""The game-side audio layer, app.aud (docs/audio-layer.md), as the
desktop game runs it.

- MusicBeat: the fixed tempo table and the time <-> beat conversions
  (getBeat, getTime, getBpm);
- SpeakerSound: one playing sound's volume, fade and stop;
- Speaker: plays effects (Sounds.xml) and songs, rooms, the "ignore
  one-shot sounds this frame" switch, pause, resume, stop all;
- Music: the current song, how a song change fades the old one out;
- SoundDefLib / SoundDef: Sounds.xml as data.SoundDef reads it
  (docs/sounds-xml-format.md), needed by Speaker.play;
- SimHost: a stand-in for HostUnity.UnityPlatformAudio (docs/audio.md)
  that keeps time, for the checks. NOT game code.

The host is anything with start, stop, setVolume, getPlayPosition and
setCategoryPause, called the way the game calls PlatformAudio.
Pure Python.
"""

import os
import struct
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cyclers import ShuffledSequence  # noqa: E402
from rand import Rand                 # noqa: E402

EFFECT, MUSIC = 0, 1           # AudioCategory_Impl_: Effect = 0, Music = 1
BEATS_PER_BAR = 4              # MusicBeat.kBeatsPerBar (its .cctor)
SECONDS_PER_MINUTE = 60.0      # DAT_180a36c98
SNAP = 0.01                    # DAT_180a6dfc0: a fade closer than this jumps to its target
STOP_LEVEL = 0.001             # DAT_180a6dfb8: a stopping sound this quiet is stopped
MUSIC_FADE = 4.0               # Speaker.music: fadeDuration boxed int 4
DEFAULT_ARG = 1.0              # DAT_180a36c38: SpeakerSound's volScale and fade when not given
SOUNDS_SEED = 23               # SoundDefLib's Rand (docs/sounds-xml-format.md)
DEFAULT_FADE = 3.0             # SoundDef: fade when Sounds.xml has none

# MusicBeat's constructor with no fixed tempo: (bar, beats per minute).
# Bars count from 1; the last entry, with no tempo, only ends the table.
# Only Music makes a MusicBeat, always this one. It fits Theme.ogg
# (scripts/checks/music_beat_check.py), not Victory or Death.
MEASURES = [(1, 100.0), (5, 102.5), (11, 105.0), (16, 107.5), (21, 110.0),
            (25, 112.5), (29, 115.0), (33, 117.5), (37, 120.0), (39, 122.5),
            (41, 125.0), (45, 125.0), (46, 110.0), (47, 100.0), (48, 90.0),
            (49, 0.0)]


def f32(x):
    """A double passed to the host as a 4-byte float."""
    return struct.unpack("<f", struct.pack("<f", x))[0]


def lerp_scale(x, in_min, in_max, out_min, out_max):
    """app.Num.lerpScale: x held to in_min..in_max, mapped onto
    out_min..out_max. (in_min == in_max would divide by zero; the data
    never asks for a fade of 0.)"""
    x = max(min(x, in_max), in_min)
    return (x - in_min) / (in_max - in_min) * (out_max - out_min) + out_min


class MusicBeat:
    """app.aud.MusicBeat. fixed_bpm (never used by the game) makes a
    one-tempo table."""

    def __init__(self, fixed_bpm=None):
        if fixed_bpm:
            self.measures = [(1, fixed_bpm), (1000, fixed_bpm)]
        else:
            self.measures = list(MEASURES)
        self.initial_bpm = self.measures[0][1]

    def _segments(self):
        for (bar0, bpm), (bar1, _) in zip(self.measures, self.measures[1:]):
            yield bpm, (int(bar1) - int(bar0)) * BEATS_PER_BAR

    def get_beat(self, time):
        """Seconds from the song's start to beats (fractional). Past the
        table's end it stays at the last beat (192)."""
        beats, t0 = 0.0, 0.0
        for bpm, n in self._segments():
            if bpm == 0.0:
                return beats
            t1 = t0 + SECONDS_PER_MINUTE / bpm * n
            beats += lerp_scale(time, t0, t1, 0.0, n)
            if time < t1:
                return beats
            t0 = t1
        return beats

    def get_time(self, beat):
        """Beats to seconds; the inverse of get_beat."""
        seconds, b0 = 0.0, 0.0
        for bpm, n in self._segments():
            if bpm == 0.0:
                return seconds
            b1 = b0 + n
            seconds += lerp_scale(beat, b0, b1, 0.0, n * (SECONDS_PER_MINUTE / bpm))
            if beat < b1:
                return seconds
            b0 = b1
        return seconds

    def get_bpm(self, beat):
        """The tempo at a beat: bar = beat / 4 + 1; the table entry whose
        bar range holds it, else the first tempo."""
        bar = beat / BEATS_PER_BAR + 1.0
        for (bar0, bpm), (bar1, _) in zip(self.measures, self.measures[1:]):
            if int(bar0) <= bar < int(bar1):
                return bpm
        return self.initial_bpm


class SpeakerSound:
    """app.aud.SpeakerSound: one sound the speaker started."""

    def __init__(self, host, play_id, category, vol_scale=None, fade=None):
        self.host = host
        self.play_id = play_id
        self.category = category
        self.vol_scale = DEFAULT_ARG if vol_scale is None else float(vol_scale)
        self.fade = DEFAULT_ARG if fade is None else float(fade)
        self.state = "PLAYING"
        self.play_position = 0.0
        self.volume = 1.0
        self.target0 = 0.0     # targetVolume0: the volume when the fade began
        self.target1 = 1.0     # targetVolume1: the volume aimed at
        self.time0 = 0.0       # targetTime0, targetTime1: the fade's span in age
        self.time1 = 0.0
        self.age = 0.0
        self.frame_count = 0

    def set_volume(self, vol, fade_to=None):
        """With fade_to: a straight-line fade from the current volume to vol
        over the sound's fade time, starting now. Without: the volume is
        set at once, and the host is NOT told (update only talks to the
        host while volume and target differ)."""
        if fade_to:
            self.time0 = self.age
            self.target0 = self.volume
            self.time1 = self.age + self.fade
        else:
            self.volume = vol
        self.target1 = vol

    def stop(self, fade_out=None):
        if fade_out:
            self.state = "STOPPING"
            self.set_volume(0.0, True)
            return
        self.state = "NONE"
        self.host.stop(self.play_id)

    def update(self, dt):
        self.age += dt
        self.frame_count += 1
        if self.volume != self.target1:
            self.volume = lerp_scale(self.age, self.time0, self.time1, self.target0, self.target1)
            if abs(self.volume - self.target1) < SNAP:
                self.volume = self.target1
            self.host.setVolume(self.play_id, f32(self.vol_scale * self.volume))
        if self.state == "STOPPING" and self.volume <= STOP_LEVEL:
            self.stop(None)
            self.state = "NONE"


class Speaker:
    """app.aud.Speaker. update(dt) takes the step of the speaker's own
    clock: real time with no 0.1 s cap (maxDeltaTime 100000), unlike the
    game's clock (docs/border-view.md)."""

    def __init__(self, host, sound_defs):
        self.host = host
        self.sound_defs = sound_defs
        self.playing = []              # playingSounds, oldest first
        self.ignoring = False          # ignoringNonLoopingPlaysThisFrame
        self.room = None
        self.cur_play_id = 0           # static Speaker.curPlayId

    def _next_play_id(self):
        self.cur_play_id += 1
        return self.cur_play_id

    def update(self, dt):
        for sound in list(self.playing):
            sound.update(dt)
            position = self.host.getPlayPosition(sound.play_id)
            if position >= 0.0:
                sound.play_position = position
            elif sound.frame_count > 1:
                self.playing.remove(sound)
        self.ignoring = False

    def ignore_non_looping_plays_this_frame(self):
        self.ignoring = True

    def set_room(self, room):
        self.room = room

    def play(self, sound_id):
        """Returns the play id, or 0 when nothing was started. The
        recording is chosen (and the sound's random order advanced) only
        when the sound does start."""
        d = self.sound_defs.get(sound_id)
        if d is None:
            return 0                   # "Sound not found: <id>" in the debug log
        if d.room is not None and self.room is not None and d.room != self.room:
            return 0
        if not d.loop and self.ignoring:
            return 0
        play_id = self._next_play_id()
        self.host.start(play_id, EFFECT, d.filename(), d.loop, f32(d.vol))
        self.playing.append(SpeakerSound(self.host, play_id, EFFECT, d.vol, d.fade))
        return play_id

    def music(self, song_id):
        """A song: "<id>.ogg", looping, volume 1, a 4-second fade. Rooms and
        the ignore switch do not apply."""
        play_id = self._next_play_id()
        self.host.start(play_id, MUSIC, song_id + ".ogg", True, 1.0)
        self.playing.append(SpeakerSound(self.host, play_id, MUSIC, 1, MUSIC_FADE))
        return play_id

    def find(self, play_id):
        for sound in self.playing:
            if sound.play_id == play_id:
                return sound
        return None

    def is_playing(self, play_id):
        return self.find(play_id) is not None

    def get_play_position(self, play_id):
        sound = self.find(play_id)
        return sound.play_position if sound is not None else 0.0

    def set_volume(self, play_id, vol, fade_to=True):
        sound = self.find(play_id)
        if sound is not None:
            sound.set_volume(vol, fade_to)

    def stop(self, play_id, fade_out=False):
        sound = self.find(play_id)
        if sound is not None:
            sound.stop(fade_out)

    def pause_all(self):
        """Pauses the EFFECT category only: songs go on."""
        self.host.setCategoryPause(EFFECT, True)

    def resume_all(self):
        self.host.setCategoryPause(EFFECT, False)

    def stop_all(self, fade_out=False, just_effects=True):
        for sound in list(self.playing):
            if not just_effects or sound.category == EFFECT:
                sound.stop(fade_out)


class Music:
    """app.aud.Music."""

    def __init__(self, speaker):
        self.speaker = speaker
        self.song_id = None
        self.want_fade_out = False
        self.beat_map = MusicBeat()
        self.play_id = 0

    def play(self, song_id):
        """The song already asked for: nothing. Otherwise, if a song is on,
        it fades out (4 s) and the new one starts once it is gone;
        None just fades out."""
        if song_id == self.song_id:
            return
        self.song_id = song_id
        if self.play_id != 0:
            self.want_fade_out = True
            self.speaker.stop(self.play_id, True)
            return
        self.play_now(self.song_id)

    def play_now(self, song_id):
        self.song_id = song_id
        self.play_id = 0
        self.want_fade_out = False
        if song_id is not None:
            self.play_id = self.speaker.music(song_id)

    def update(self):
        if self.want_fade_out and not self.speaker.is_playing(self.play_id):
            self.play_now(self.song_id)

    @property
    def is_playing(self):
        return self.speaker.is_playing(self.play_id)

    @property
    def beat(self):
        return self.beat_map.get_beat(self.speaker.get_play_position(self.play_id))


# ---- Sounds.xml (data.SoundDefLib, data.SoundDef) ---------------------------

class SoundDef:
    def __init__(self, rand, node):
        self.id = node.get("id")
        self.files = node.get("file").split(" ") if node.get("file") is not None else [self.id + ".wav"]
        self.loop = node.get("loop") == "true"
        self.vol = float(node.get("vol")) if node.get("vol") is not None else 1.0
        self.has_fade = node.get("fade") is not None
        self.fade = float(node.get("fade")) if self.has_fade else DEFAULT_FADE
        self.room = node.get("room")
        self.rand = rand
        # More than two recordings: a shuffled order over THREE of them.
        self.sequence = ShuffledSequence(3, rand.next_int()) if len(self.files) > 2 else None

    def filename(self):
        if len(self.files) == 1:
            return self.files[0]
        if self.sequence is None:      # exactly two: no sound has two; the
            # form of this one draw was not checked against the code
            return self.files[int(len(self.files) * self.rand.next_float())]
        return self.files[self.sequence.next()]


class SoundDefLib:
    def __init__(self, sounds_xml_path):
        root = ET.parse(sounds_xml_path).getroot()
        rand = Rand(SOUNDS_SEED)
        self.defs = {}
        for node in root.findall("sound"):
            d = SoundDef(rand, node)
            if d.id in self.defs:
                raise ValueError("Sound already exists: " + d.id)
            self.defs[d.id] = d

    def get(self, sound_id):
        return self.defs.get(sound_id)


# ---- a stand-in for the host, for checks (NOT game code) --------------------

class SimHost:
    """Keeps a clock and answers like UnityPlatformAudio: a position in
    seconds, or -1 once a sound is stopped or (not looping) finished.
    lengths: file name -> seconds. Records every call in self.log."""

    def __init__(self, lengths):
        self.lengths = lengths
        self.time = 0.0
        self.sounds = {}               # play id -> dict
        self.paused = {EFFECT: False, MUSIC: False}
        self.log = []

    def advance(self, dt):
        self.time += dt
        for s in self.sounds.values():
            if not s["paused"]:
                s["pos"] += dt

    def start(self, play_id, category, filename, loop, volume):
        self.log.append(("start", play_id, category, filename, loop, volume))
        if filename not in self.lengths:
            return
        self.sounds[play_id] = {"file": filename, "loop": loop, "volume": volume,
                                "category": category, "pos": 0.0, "paused": False}

    def stop(self, play_id):
        self.log.append(("stop", play_id))
        self.sounds.pop(play_id, None)

    def setVolume(self, play_id, volume):
        self.log.append(("setVolume", play_id, volume))
        if play_id in self.sounds:
            self.sounds[play_id]["volume"] = volume

    def getPlayPosition(self, play_id):
        s = self.sounds.get(play_id)
        if s is None:
            return -1.0
        length = self.lengths[s["file"]]
        if s["loop"]:
            return f32(s["pos"] % length)
        if s["pos"] >= length:
            del self.sounds[play_id]   # the host's Update frees a finished source
            return -1.0
        return f32(s["pos"])

    def setCategoryPause(self, category, pause):
        self.log.append(("setCategoryPause", category, pause))
        for s in self.sounds.values():
            if s["category"] == category:
                s["paused"] = pause

    def volume(self, play_id):
        s = self.sounds.get(play_id)
        return None if s is None else s["volume"]
