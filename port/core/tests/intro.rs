//! Plays the intro (milestone 3c) frame by frame through the game, with real
//! mouse presses, and compares it with the Python reference's run: every
//! frame's page, state, wipe cut, letters shown and NEXT; the frames on
//! which `text-reveal` plays; six pictures byte for byte; the frame the
//! pages end on. Then the fade to the title (the port's stand-in for the
//! day-1 newspaper). Needs two gitignored, game-derived inputs; with either
//! missing the test says so and passes without checking:
//!
//!     python -I scripts/build_assets/build_pack.py          -> build/assets/start.pack
//!     python -I scripts/reference/introscreen.py extracted/art/assets extracted/previews/m3c

use std::path::{Path, PathBuf};

use pp_core::aud::{AudioHost, SoundDefs};
use pp_core::fade::State as Change;
use pp_core::game::{Game, GameScreen, Platform};
use pp_core::input::HostInput;
use pp_core::intro::State;
use pp_core::pack::Pack;
use pp_core::pages::Gallery;
use pp_core::raster::Screen;
use pp_core::settings::{Saved, Settings};
use pp_core::sound::Category;

mod common;
use common::Json;

const DT: f64 = 1.0 / 60.0;
/// Inside NEXT (129 x 19 at (220, 290)).
const NEXT: (f64, f64) = (285.0, 299.0);

#[derive(Default)]
struct Audio {
    started: Vec<String>,
}

impl AudioHost for Audio {
    fn start(&mut self, _: u32, _: Category, file: &str, _: bool, _: f32) {
        self.started.push(file.to_string());
    }
    fn stop(&mut self, _: u32) {}
    fn set_volume(&mut self, _: u32, _: f32) {}
    fn position(&mut self, _: u32) -> f64 {
        1.0
    }
    fn set_category_pause(&mut self, _: Category, _: bool) {}
    fn set_category_volume(&mut self, _: Category, _: f32) {}
}

struct Page;

impl Platform for Page {
    fn fullscreen(&mut self) -> bool {
        false
    }
    fn set_fullscreen(&mut self, _: bool) {}
    fn save_settings(&mut self, _: &Saved) {}
}

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// One frame of the run as the game shows it: (page, state, cut, letters
/// shown, NEXT shown).
type Frame = (usize, &'static str, Option<i64>, usize, bool);

#[test]
fn the_intro_plays_as_the_reference_does() {
    let pack_path = root().join("build/assets/start.pack");
    let out = root().join("extracted/previews/m3c");
    let Ok(bytes) = std::fs::read(&pack_path) else {
        eprintln!("SKIPPED: {} not found", pack_path.display());
        return;
    };
    let Ok(timeline) = std::fs::read_to_string(out.join("timeline.json")) else {
        eprintln!("SKIPPED: {} not found", out.join("timeline.json").display());
        return;
    };
    let timeline = Json::parse(&timeline);
    let pack = Pack::parse(bytes).unwrap();
    let mut gallery = Gallery::from_pack(&pack).unwrap();
    let defs = SoundDefs::parse(std::str::from_utf8(pack.get("data/Sounds.xml").unwrap()).unwrap()).unwrap();
    let mut game = Game::new_intro(defs, Settings::new(true, None));
    let (mut audio, mut page) = (Audio::default(), Page);

    // The run's inputs, from the reference's events: NEXT pressed the frame
    // before and let go on the frame; a hurry pressed on the frame and let
    // go on the next. All on NEXT's spot, where the mouse stays.
    let mut down_on = std::collections::BTreeSet::new();
    for e in timeline.get("events").list() {
        let f = e.get("frame").num().unwrap();
        match e.get("what").str() {
            "next" => down_on.insert(f - 1),
            _ => down_on.insert(f),
        };
    }
    let done = timeline.get("done").num().unwrap();
    let snapshots: Vec<(String, i64)> = match timeline.get("snapshots") {
        Json::Obj(items) => items.iter().map(|(k, v)| (k.clone(), v.num().unwrap())).collect(),
        _ => panic!(),
    };

    let mut frames: Vec<Frame> = Vec::new();
    let mut reveals = Vec::new();
    let mut checked = 0;
    for frame in 1..=done {
        let host = HostInput { mouse_valid: true, mouse: NEXT, left_down: down_on.contains(&frame), ..HostInput::default() };
        let before = audio.started.len();
        game.step(&host, DT, &mut gallery, &mut audio, &mut page).unwrap();
        if audio.started[before..].iter().any(|f| f.starts_with("text-reveal")) {
            reveals.push(frame);
        }
        let GameScreen::Intro(intro) = game.screen() else { panic!("frame {frame}: not on the intro") };
        let p = &intro.player;
        let state = match p.state() {
            State::Flipping => "flipping",
            State::Idle => "idle",
        };
        frames.push((p.page_index(), state, p.cut().map(i64::from), p.shown(), p.next_visible()));
        for (name, at) in &snapshots {
            if *at == frame {
                let want = std::fs::read(out.join(format!("{name}.rgba"))).unwrap();
                let mut screen = Screen::new();
                for q in intro.quads(&gallery) {
                    screen.draw(&q, &gallery.pictures);
                }
                let differing = screen.pixels.iter().zip(&want).filter(|(a, b)| a != b).count();
                assert_eq!(differing, 0, "{name} (frame {frame}): {differing} bytes differ from the reference");
                eprintln!("{name} (frame {frame}) is identical to the reference");
                checked += 1;
            }
        }
    }
    assert_eq!(checked, snapshots.len());

    // Every frame against the reference's.
    let want: Vec<Frame> = timeline
        .get("frames")
        .list()
        .iter()
        .map(|f| {
            let state = if f.get("state").str() == "idle" { "idle" } else { "flipping" };
            let next = f.get("next") == &Json::Bool(true);
            (f.get("page").num().unwrap() as usize, state, f.get("cut").num(), f.get("shown").num().unwrap() as usize, next)
        })
        .collect();
    assert_eq!(frames.len(), want.len());
    for (i, (got, want)) in frames.iter().zip(&want).enumerate() {
        assert_eq!(got, want, "frame {}", i + 1);
    }
    let want_reveals: Vec<i64> = timeline.get("text_reveal").list().iter().map(|j| j.num().unwrap()).collect();
    // A frame with two letters' sounds would count once here; at 0.04 s a
    // letter and 1/60 s a frame none has two.
    let mut unique = want_reveals.clone();
    unique.dedup();
    assert_eq!(reveals, unique, "the frames text-reveal plays on");
    eprintln!("{} frames, text-reveal on {} frames: as the reference; the pages end on frame {done}", frames.len(), reveals.len());

    // The last NEXT starts the fade (to the title, for now); the title is
    // built on the 70th frame and does not rise.
    assert_eq!(game.change_state(), Change::Off);
    for _ in 0..69 {
        game.step(&HostInput { mouse_valid: true, mouse: NEXT, ..HostInput::default() }, DT, &mut gallery, &mut audio, &mut page).unwrap();
        assert!(matches!(game.screen(), GameScreen::Intro(_)));
    }
    game.step(&HostInput { mouse_valid: true, mouse: NEXT, ..HostInput::default() }, DT, &mut gallery, &mut audio, &mut page).unwrap();
    let GameScreen::Title(title) = game.screen() else { panic!("not the title 70 frames after the last NEXT") };
    assert!(!title.rising());
    assert_eq!(audio.started.iter().filter(|f| *f == "Theme.ogg").count(), 1, "Theme started once and played on");
}
