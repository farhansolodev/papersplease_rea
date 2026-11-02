//! The game-side audio layer, `app.aud` (docs/audio-layer.md), as the
//! desktop game runs it; the same as scripts/reference/aud.py.
//!
//! - [`SoundDefs`]: `Sounds.xml` (docs/sounds-xml-format.md);
//! - [`Speaker`]: plays effects and songs, keeps each playing sound's volume
//!   and fade ([`SpeakerSound`]), rooms, the "ignore one-shot sounds this
//!   frame" switch, pause, resume, stop all;
//! - [`Music`]: the current song, a song change fading the old one out;
//! - [`MusicBeat`]: the fixed tempo table and the time to beat conversion.
//!
//! The sound player itself is the host's ([`AudioHost`]): in the browser the
//! page's `audio.js`, as `UnityPlatformAudio` in the original.

use crate::num::lerp_scale;
use crate::rand::{Rand, ShuffledSequence};
use crate::sound::Category;
use crate::xmlscan;

/// What the game asks of the host's sound player (`PlatformAudio`).
pub trait AudioHost {
    fn start(&mut self, id: u32, category: Category, file: &str, looping: bool, volume: f32);
    fn stop(&mut self, id: u32);
    fn set_volume(&mut self, id: u32, volume: f32);
    /// The sound's position in seconds, or below 0 when the player does not
    /// have it (stopped, finished, or never started).
    fn position(&mut self, id: u32) -> f64;
    fn set_category_pause(&mut self, category: Category, paused: bool);
    /// A category's mixer volume, 0 to 1 (`Game.applySettings` gives each
    /// its setting squared; docs/audio.md, "The mixer").
    fn set_category_volume(&mut self, category: Category, volume: f32);
}

/// MusicBeat.kBeatsPerBar.
const BEATS_PER_BAR: f64 = 4.0;
/// A fade closer than this to its target jumps to it.
const SNAP: f64 = 0.01;
/// A stopping sound this quiet is stopped.
const STOP_LEVEL: f64 = 0.001;
/// `Speaker.music`: a song's fade.
const MUSIC_FADE: f64 = 4.0;
/// `SoundDef`: the fade when `Sounds.xml` gives none.
const DEFAULT_FADE: f64 = 3.0;
/// The seed of `SoundDefLib`'s generator.
const SOUNDS_SEED: i32 = 23;

/// `MusicBeat`'s table: (bar, beats per minute); bars count from 1, and the
/// last entry, with no tempo, only ends the table. It fits `Theme`
/// (scripts/checks/music_beat_check.py).
const MEASURES: [(i32, f64); 16] = [
    (1, 100.0),
    (5, 102.5),
    (11, 105.0),
    (16, 107.5),
    (21, 110.0),
    (25, 112.5),
    (29, 115.0),
    (33, 117.5),
    (37, 120.0),
    (39, 122.5),
    (41, 125.0),
    (45, 125.0),
    (46, 110.0),
    (47, 100.0),
    (48, 90.0),
    (49, 0.0),
];

/// A double handed to the host as a 4-byte float.
fn f32_of(x: f64) -> f32 {
    x as f32
}

/// `app.aud.MusicBeat`, with the one table the game uses.
pub struct MusicBeat;

impl MusicBeat {
    /// Seconds from the song's start to beats, with a fraction. Past the
    /// table's end it stays at the last beat (192).
    pub fn beat(time: f64) -> f64 {
        let (mut beats, mut t0) = (0.0, 0.0);
        for pair in MEASURES.windows(2) {
            let ((bar0, bpm), (bar1, _)) = (pair[0], pair[1]);
            let n = (bar1 - bar0) as f64 * BEATS_PER_BAR;
            if bpm == 0.0 {
                return beats;
            }
            let t1 = t0 + 60.0 / bpm * n;
            beats += lerp_scale(time, t0, t1, 0.0, n);
            if time < t1 {
                return beats;
            }
            t0 = t1;
        }
        beats
    }
}

/// One sound of `Sounds.xml` (`data.SoundDef`).
struct SoundDef {
    id: String,
    files: Vec<String>,
    looping: bool,
    vol: f64,
    fade: f64,
    room: Option<String>,
    /// More than two recordings: a shuffled order over three of them.
    sequence: Option<ShuffledSequence>,
}

/// `Sounds.xml` as `data.SoundDefLib` reads it. The order of the file
/// matters: every sound with more than two recordings takes one draw from
/// the one generator, in file order.
pub struct SoundDefs {
    defs: Vec<SoundDef>,
    /// Picks between exactly two recordings (no sound has two).
    rand: Rand,
}

impl SoundDefs {
    pub fn parse(xml: &str) -> Result<SoundDefs, String> {
        let mut rand = Rand::new(SOUNDS_SEED);
        let mut defs: Vec<SoundDef> = Vec::new();
        for tag in xmlscan::tags(xml).into_iter().filter(|t| t.name == "sound") {
            let id = tag.attr("id").ok_or("a sound without an id")?.to_string();
            if defs.iter().any(|d| d.id == id) {
                return Err(format!("Sound already exists: {id}"));
            }
            let files: Vec<String> = match tag.attr("file") {
                Some(f) => f.split(' ').map(String::from).collect(),
                None => vec![format!("{id}.wav")],
            };
            let number = |name: &str, default: f64| -> Result<f64, String> {
                tag.attr(name).map_or(Ok(default), |v| v.trim().parse().map_err(|_| format!("{id}: bad {name} {v:?}")))
            };
            let sequence = (files.len() > 2).then(|| ShuffledSequence::new(3, rand.next_int()));
            defs.push(SoundDef {
                looping: tag.attr("loop") == Some("true"),
                vol: number("vol", 1.0)?,
                fade: number("fade", DEFAULT_FADE)?,
                room: tag.attr("room").map(String::from),
                id,
                files,
                sequence,
            });
        }
        Ok(SoundDefs { defs, rand })
    }

    pub fn len(&self) -> usize {
        self.defs.len()
    }

    pub fn is_empty(&self) -> bool {
        self.defs.is_empty()
    }

    fn get(&self, id: &str) -> Option<usize> {
        self.defs.iter().position(|d| d.id == id)
    }

    /// The recording to play now; advances the sound's order.
    fn filename(&mut self, index: usize) -> String {
        let d = &mut self.defs[index];
        match (&mut d.sequence, d.files.len()) {
            (_, 1) => d.files[0].clone(),
            (Some(seq), _) => d.files[seq.next()].clone(),
            (None, n) => d.files[(n as f64 * self.rand.next_float()) as usize].clone(),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum State {
    Playing,
    Stopping,
    None,
}

/// `app.aud.SpeakerSound`: one sound the speaker started.
pub struct SpeakerSound {
    play_id: u32,
    category: Category,
    vol_scale: f64,
    fade: f64,
    state: State,
    play_position: f64,
    volume: f64,
    /// The volume when the fade began, and the one aimed at.
    target0: f64,
    target1: f64,
    /// The fade's span, in the sound's age.
    time0: f64,
    time1: f64,
    age: f64,
    frame_count: u32,
}

impl SpeakerSound {
    fn new(play_id: u32, category: Category, vol_scale: f64, fade: f64) -> SpeakerSound {
        SpeakerSound {
            play_id,
            category,
            vol_scale,
            fade,
            state: State::Playing,
            play_position: 0.0,
            volume: 1.0,
            target0: 0.0,
            target1: 1.0,
            time0: 0.0,
            time1: 0.0,
            age: 0.0,
            frame_count: 0,
        }
    }

    /// With `fade`: a straight-line fade from the current volume over the
    /// sound's fade time, from now. Without: the volume is set at once and
    /// the host is NOT told (`update` talks to the host only while the
    /// volume and the target differ; docs/audio-layer.md).
    fn set_volume(&mut self, vol: f64, fade: bool) {
        if fade {
            self.time0 = self.age;
            self.target0 = self.volume;
            self.time1 = self.age + self.fade;
        } else {
            self.volume = vol;
        }
        self.target1 = vol;
    }

    fn stop(&mut self, fade_out: bool, host: &mut dyn AudioHost) {
        if fade_out {
            self.state = State::Stopping;
            self.set_volume(0.0, true);
            return;
        }
        self.state = State::None;
        host.stop(self.play_id);
    }

    fn update(&mut self, dt: f64, host: &mut dyn AudioHost) {
        self.age += dt;
        self.frame_count += 1;
        if self.volume != self.target1 {
            self.volume = lerp_scale(self.age, self.time0, self.time1, self.target0, self.target1);
            if (self.volume - self.target1).abs() < SNAP {
                self.volume = self.target1;
            }
            host.set_volume(self.play_id, f32_of(self.vol_scale * self.volume));
        }
        if self.state == State::Stopping && self.volume <= STOP_LEVEL {
            self.stop(false, host);
        }
    }
}

/// `app.aud.Speaker`.
pub struct Speaker {
    defs: SoundDefs,
    /// Oldest first.
    playing: Vec<SpeakerSound>,
    ignoring: bool,
    room: Option<String>,
    /// `Speaker.curPlayId`, kept for the whole run.
    cur_play_id: u32,
}

impl Speaker {
    pub fn new(defs: SoundDefs) -> Speaker {
        Speaker { defs, playing: Vec::new(), ignoring: false, room: None, cur_play_id: 0 }
    }

    /// Once a frame, with the speaker's own clock: real time with no cap.
    pub fn update(&mut self, dt: f64, host: &mut dyn AudioHost) {
        let mut i = 0;
        while i < self.playing.len() {
            let sound = &mut self.playing[i];
            sound.update(dt, host);
            let position = host.position(sound.play_id);
            if position >= 0.0 {
                sound.play_position = position as f32 as f64;
            } else if sound.frame_count > 1 {
                self.playing.remove(i);
                continue;
            }
            i += 1;
        }
        self.ignoring = false;
    }

    pub fn ignore_non_looping_plays_this_frame(&mut self) {
        self.ignoring = true;
    }

    pub fn set_room(&mut self, room: Option<String>) {
        self.room = room;
    }

    fn next_play_id(&mut self) -> u32 {
        self.cur_play_id += 1;
        self.cur_play_id
    }

    /// Plays an effect of `Sounds.xml`; the play id, or 0 when nothing was
    /// started. The recording is chosen only when the sound does start.
    pub fn play(&mut self, id: &str, host: &mut dyn AudioHost) -> u32 {
        let Some(index) = self.defs.get(id) else { return 0 };
        let d = &self.defs.defs[index];
        if let (Some(room), Some(current)) = (&d.room, &self.room) {
            if room != current {
                return 0;
            }
        }
        if !d.looping && self.ignoring {
            return 0;
        }
        let (looping, vol, fade) = (d.looping, d.vol, d.fade);
        let play_id = self.next_play_id();
        let file = self.defs.filename(index);
        host.start(play_id, Category::Effect, &file, looping, f32_of(vol));
        self.playing.push(SpeakerSound::new(play_id, Category::Effect, vol, fade));
        play_id
    }

    /// A song: "<id>.ogg", looping, volume 1, a 4-second fade. Rooms and the
    /// ignore switch do not apply.
    pub fn music(&mut self, song: &str, host: &mut dyn AudioHost) -> u32 {
        let play_id = self.next_play_id();
        host.start(play_id, Category::Music, &format!("{song}.ogg"), true, 1.0);
        self.playing.push(SpeakerSound::new(play_id, Category::Music, 1.0, MUSIC_FADE));
        play_id
    }

    fn find(&mut self, play_id: u32) -> Option<&mut SpeakerSound> {
        self.playing.iter_mut().find(|s| s.play_id == play_id)
    }

    pub fn is_playing(&self, play_id: u32) -> bool {
        self.playing.iter().any(|s| s.play_id == play_id)
    }

    pub fn play_position(&self, play_id: u32) -> f64 {
        self.playing.iter().find(|s| s.play_id == play_id).map_or(0.0, |s| s.play_position)
    }

    pub fn set_volume(&mut self, play_id: u32, vol: f64, fade: bool) {
        if let Some(s) = self.find(play_id) {
            s.set_volume(vol, fade);
        }
    }

    pub fn stop(&mut self, play_id: u32, fade_out: bool, host: &mut dyn AudioHost) {
        if let Some(s) = self.find(play_id) {
            s.stop(fade_out, host);
        }
    }

    /// Pauses the effects only: songs go on.
    pub fn pause_all(&mut self, host: &mut dyn AudioHost) {
        host.set_category_pause(Category::Effect, true);
    }

    pub fn resume_all(&mut self, host: &mut dyn AudioHost) {
        host.set_category_pause(Category::Effect, false);
    }

    pub fn stop_all(&mut self, fade_out: bool, just_effects: bool, host: &mut dyn AudioHost) {
        for s in &mut self.playing {
            if !just_effects || s.category == Category::Effect {
                s.stop(fade_out, host);
            }
        }
    }
}

/// `app.aud.Music`.
#[derive(Default)]
pub struct Music {
    song: Option<String>,
    want_fade_out: bool,
    play_id: u32,
}

impl Music {
    pub fn new() -> Music {
        Music::default()
    }

    /// The song already asked for: nothing. Otherwise a song that is on
    /// fades out (4 s) and the new one starts once it has gone; `None` only
    /// fades out.
    pub fn play(&mut self, song: Option<&str>, speaker: &mut Speaker, host: &mut dyn AudioHost) {
        if song == self.song.as_deref() {
            return;
        }
        self.song = song.map(String::from);
        if self.play_id != 0 {
            self.want_fade_out = true;
            speaker.stop(self.play_id, true, host);
            return;
        }
        self.play_now(speaker, host);
    }

    fn play_now(&mut self, speaker: &mut Speaker, host: &mut dyn AudioHost) {
        self.play_id = 0;
        self.want_fade_out = false;
        if let Some(song) = &self.song {
            self.play_id = speaker.music(song, host);
        }
    }

    pub fn update(&mut self, speaker: &mut Speaker, host: &mut dyn AudioHost) {
        if self.want_fade_out && !speaker.is_playing(self.play_id) {
            self.play_now(speaker, host);
        }
    }

    pub fn is_playing(&self, speaker: &Speaker) -> bool {
        speaker.is_playing(self.play_id)
    }

    pub fn beat(&self, speaker: &Speaker) -> f64 {
        MusicBeat::beat(speaker.play_position(self.play_id))
    }
}

/// A stand-in for the host's sound player, for tests: keeps a clock and
/// answers like `UnityPlatformAudio` (a position, or -1 once a sound is
/// stopped or, not looping, finished). The same as aud.py's `SimHost`.
#[cfg(test)]
pub(crate) mod sim {
    use super::*;

    pub struct SimSound {
        pub file: String,
        pub looping: bool,
        pub volume: f32,
        pub category: Category,
        pub pos: f64,
        pub paused: bool,
    }

    #[derive(Default)]
    pub struct SimHost {
        /// File name and its length in seconds.
        pub lengths: Vec<(String, f64)>,
        pub sounds: Vec<(u32, SimSound)>,
        pub log: Vec<String>,
    }

    impl SimHost {
        pub fn new(lengths: &[(&str, f64)]) -> SimHost {
            SimHost { lengths: lengths.iter().map(|(f, l)| (f.to_string(), *l)).collect(), ..SimHost::default() }
        }

        pub fn advance(&mut self, dt: f64) {
            for (_, s) in &mut self.sounds {
                if !s.paused {
                    s.pos += dt;
                }
            }
        }

        pub fn volume(&self, id: u32) -> Option<f32> {
            self.sounds.iter().find(|(i, _)| *i == id).map(|(_, s)| s.volume)
        }
    }

    impl AudioHost for SimHost {
        fn start(&mut self, id: u32, category: Category, file: &str, looping: bool, volume: f32) {
            self.log.push(format!("start {id} {category:?} {file} {looping} {volume}"));
            if self.lengths.iter().any(|(f, _)| f == file) {
                let sound = SimSound { file: file.into(), looping, volume, category, pos: 0.0, paused: false };
                self.sounds.push((id, sound));
            }
        }
        fn stop(&mut self, id: u32) {
            self.log.push(format!("stop {id}"));
            self.sounds.retain(|(i, _)| *i != id);
        }
        fn set_volume(&mut self, id: u32, volume: f32) {
            self.log.push(format!("setVolume {id} {volume}"));
            if let Some((_, s)) = self.sounds.iter_mut().find(|(i, _)| *i == id) {
                s.volume = volume;
            }
        }
        fn position(&mut self, id: u32) -> f64 {
            let Some(at) = self.sounds.iter().position(|(i, _)| *i == id) else { return -1.0 };
            let s = &self.sounds[at].1;
            let length = self.lengths.iter().find(|(f, _)| *f == s.file).unwrap().1;
            if s.looping {
                return (s.pos % length) as f32 as f64;
            }
            if s.pos >= length {
                self.sounds.remove(at);
                return -1.0;
            }
            s.pos as f32 as f64
        }
        fn set_category_pause(&mut self, category: Category, paused: bool) {
            self.log.push(format!("setCategoryPause {category:?} {paused}"));
            for (_, s) in &mut self.sounds {
                if s.category == category {
                    s.paused = paused;
                }
            }
        }
        fn set_category_volume(&mut self, category: Category, volume: f32) {
            self.log.push(format!("setCategoryVolume {category:?} {volume}"));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::sim::SimHost;
    use super::*;

    const XML: &str = r#"<sounds>
        <!-- <sound id="gone"/> -->
        <sound id="button-down"/>
        <sound id="loop" loop="true" vol="0.5" fade="2"/>
        <sound id="three" file="a.wav b.wav c.wav"/>
        <sound id="booth" room="booth"/>
    </sounds>"#;

    #[test]
    fn the_beat_follows_the_tempo_table() {
        // python -I -c "from aud import MusicBeat; b = MusicBeat(); ..."
        // (scripts/reference), values printed with repr.
        for (time, beat) in [
            (0.0, 0.0),
            (0.6, 1.0),
            (9.6, 16.0),
            (10.0, 16.683333333333334),
            (23.4, 39.574999999999996),
            (100.0, 184.46837823945384),
            (500.0, 192.0),
        ] {
            assert!((MusicBeat::beat(time) - beat).abs() < 1e-9, "time {time}: {} not {beat}", MusicBeat::beat(time));
        }
    }

    #[test]
    fn reads_sounds_xml() {
        let defs = SoundDefs::parse(XML).unwrap();
        assert_eq!(defs.len(), 4);
        let d = &defs.defs[defs.get("loop").unwrap()];
        assert!(d.looping && d.vol == 0.5 && d.fade == 2.0);
        assert_eq!(defs.defs[defs.get("button-down").unwrap()].files, ["button-down.wav"]);
        assert_eq!(defs.defs[0].fade, DEFAULT_FADE);
        assert!(SoundDefs::parse(r#"<sound id="x"/><sound id="x"/>"#).is_err());
    }

    /// The game's own `Sounds.xml` (gitignored, game-derived; skipped when
    /// missing) read as aud.py's `SoundDefLib` reads it: 94 sounds, and
    /// the same recording picks for every sound with several. The numbers
    /// were printed by aud.py on 2026-11-03.
    #[test]
    fn the_games_sounds_xml_matches_the_reference() {
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../extracted/art/assets/data/Sounds.xml");
        let Ok(xml) = std::fs::read_to_string(&path) else {
            eprintln!("SKIPPED: {} not found", path.display());
            return;
        };
        let mut defs = SoundDefs::parse(&xml).unwrap();
        assert_eq!(defs.len(), 94);
        let loops = defs.defs.iter().filter(|d| d.looping).count();
        let vol: f64 = defs.defs.iter().map(|d| d.vol).sum();
        let fade: f64 = defs.defs.iter().map(|d| d.fade).sum();
        let rooms = defs.defs.iter().filter(|d| d.room.is_some()).count();
        assert_eq!((loops, rooms), (2, 1));
        assert!((vol - 77.225).abs() < 1e-6 && (fade - 278.0).abs() < 1e-6);
        let want: [(usize, usize, [usize; 7]); 9] = [
            (16, 3, [1, 2, 0, 1, 2, 0, 1]),
            (38, 3, [1, 2, 0, 1, 2, 0, 1]),
            (39, 3, [0, 2, 1, 0, 2, 1, 0]),
            (40, 3, [2, 1, 0, 2, 1, 0, 2]),
            (41, 3, [2, 0, 1, 2, 0, 1, 2]),
            (43, 3, [2, 1, 0, 2, 1, 0, 2]),
            (44, 3, [1, 0, 2, 1, 0, 2, 1]),
            (68, 4, [2, 0, 1, 2, 0, 1, 2]),
            (77, 4, [2, 0, 1, 2, 0, 1, 2]),
        ];
        let several: Vec<usize> = (0..defs.len()).filter(|&i| defs.defs[i].files.len() > 1).collect();
        assert_eq!(several, want.iter().map(|w| w.0).collect::<Vec<_>>());
        for (index, count, picks) in want {
            assert_eq!(defs.defs[index].files.len(), count);
            let got: Vec<usize> = (0..7)
                .map(|_| {
                    let file = defs.filename(index);
                    defs.defs[index].files.iter().position(|f| *f == file).unwrap()
                })
                .collect();
            assert_eq!(got, picks, "sound {index}");
        }
    }

    #[test]
    fn an_effect_is_started_with_its_volume_and_freed_when_done() {
        let mut host = SimHost::new(&[("button-down.wav", 0.1)]);
        let mut speaker = Speaker::new(SoundDefs::parse(XML).unwrap());
        assert_eq!(speaker.play("nothing", &mut host), 0);
        let id = speaker.play("button-down", &mut host);
        assert_eq!(id, 1);
        assert_eq!(host.log, ["start 1 Effect button-down.wav false 1"]);
        speaker.update(1.0 / 60.0, &mut host);
        assert!(speaker.is_playing(id));
        host.advance(0.2);
        speaker.update(1.0 / 60.0, &mut host);
        assert!(!speaker.is_playing(id));
    }

    #[test]
    fn rooms_and_the_ignore_switch() {
        let mut host = SimHost::new(&[]);
        let mut speaker = Speaker::new(SoundDefs::parse(XML).unwrap());
        speaker.set_room(Some("street".into()));
        assert_eq!(speaker.play("booth", &mut host), 0);
        speaker.ignore_non_looping_plays_this_frame();
        assert_eq!(speaker.play("button-down", &mut host), 0);
        assert_ne!(speaker.play("loop", &mut host), 0);
        speaker.update(0.0, &mut host);
        assert_ne!(speaker.play("button-down", &mut host), 0);
    }

    #[test]
    fn a_song_change_fades_the_old_song_out_over_4_s() {
        let mut host = SimHost::new(&[("Theme.ogg", 100.0), ("Death.ogg", 100.0)]);
        let mut speaker = Speaker::new(SoundDefs::parse(XML).unwrap());
        let mut music = Music::new();
        music.play(Some("Theme"), &mut speaker, &mut host);
        let theme = 1;
        assert!(music.is_playing(&speaker));
        music.play(Some("Theme"), &mut speaker, &mut host);
        assert_eq!(host.log.len(), 1, "the same song again does nothing");
        music.play(Some("Death"), &mut speaker, &mut host);
        let dt = 1.0 / 60.0;
        let mut frames = 0;
        while host.sounds.iter().all(|(_, s)| s.file != "Death.ogg") {
            host.advance(dt);
            speaker.update(dt, &mut host);
            music.update(&mut speaker, &mut host);
            frames += 1;
            if frames == 120 {
                // Halfway: the volume is a straight line from 1 to 0.
                assert!((host.volume(theme).unwrap() - 0.5).abs() < 0.01);
            }
            assert!(frames < 300);
        }
        // aud.py with the same steps: 238 frames.
        assert_eq!(frames, 238);
        assert!(host.log.contains(&"stop 1".to_string()));
        assert!(host.log.last().unwrap().starts_with("start 2 Music Death.ogg true 1"));
    }

    #[test]
    fn an_instant_volume_change_never_reaches_the_host() {
        let mut host = SimHost::new(&[]);
        let mut speaker = Speaker::new(SoundDefs::parse(XML).unwrap());
        let id = speaker.play("loop", &mut host);
        speaker.set_volume(id, 0.2, false);
        speaker.update(0.1, &mut host);
        assert!(!host.log.iter().any(|l| l.starts_with("setVolume")));
        speaker.set_volume(id, 0.0, true);
        speaker.update(1.0, &mut host);
        // Half of the 2 s fade from 0.2: 0.1, times the sound's 0.5.
        assert!(host.log.last().unwrap().starts_with("setVolume 1 0.05"));
    }

    #[test]
    fn effects_pause_and_songs_go_on() {
        let mut host = SimHost::new(&[]);
        let mut speaker = Speaker::new(SoundDefs::parse(XML).unwrap());
        speaker.pause_all(&mut host);
        speaker.resume_all(&mut host);
        assert_eq!(host.log, ["setCategoryPause Effect true", "setCategoryPause Effect false"]);
    }
}
