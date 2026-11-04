//! Plays the start of day 1 (milestone 4a) frame by frame through the game
//! and compares it with the Python reference's run: every frame's booth and
//! border states, whether the opening card shows and its exact y, how many
//! letters of the date are out, the booth button's look; the frames on
//! which the sounds start; six pictures byte for byte. Needs two
//! gitignored, game-derived inputs; with either missing the test says so
//! and passes without checking:
//!
//!     python -I scripts/build_assets/build_pack.py          -> build/assets/start.pack
//!     python -I scripts/reference/boothscreen.py extracted/art/assets extracted/previews/m4a

use std::path::{Path, PathBuf};

use pp_core::aud::{AudioHost, SoundDefs};
use pp_core::game::{Game, GameScreen, Platform};
use pp_core::input::HostInput;
use pp_core::pack::Pack;
use pp_core::pages::Gallery;
use pp_core::raster::Screen;
use pp_core::settings::{Saved, Settings};
use pp_core::sound::Category;

mod common;
use common::Json;

const DT: f64 = 1.0 / 60.0;

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

/// One frame as the game shows it: booth state, border state, card shown,
/// card y, letters shown, button look.
type Frame = (String, String, bool, f64, usize, String);

#[test]
fn the_start_of_day_one_plays_as_the_reference_does() {
    let pack_path = root().join("build/assets/start.pack");
    let out = root().join("extracted/previews/m4a");
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
    let mut game = Game::new_day(defs, Settings::new(true, None));
    let (mut audio, mut page) = (Audio::default(), Page);
    let snapshots: Vec<(String, i64)> = match timeline.get("snapshots") {
        Json::Obj(items) => items.iter().map(|(k, v)| (k.clone(), v.num().unwrap())).collect(),
        _ => panic!(),
    };
    let want_frames = timeline.get("frames").list();

    let mut frames: Vec<Frame> = Vec::new();
    let mut sounds: Vec<(i64, String)> = Vec::new();
    let mut checked = 0;
    for frame in 1..=want_frames.len() as i64 {
        let before = audio.started.len();
        game.step(&HostInput::default(), DT, &mut gallery, &mut audio, &mut page).unwrap();
        for file in &audio.started[before..] {
            for id in ["text-reveal", "booth-intro", "border-ambient", "booth-ambient"] {
                if file.starts_with(id) && sounds.last() != Some(&(frame, id.to_string())) {
                    sounds.push((frame, id.to_string()));
                }
            }
        }
        let GameScreen::Day(day) = game.screen() else { panic!("frame {frame}: not on the day screen") };
        let (shown, y) = day.card();
        frames.push((
            day.booth_state().into(),
            day.border_state().into(),
            shown,
            y,
            day.shown(),
            day.button_look().into(),
        ));
        for (name, at) in &snapshots {
            if *at == frame {
                let want = std::fs::read(out.join(format!("{name}.rgba"))).unwrap();
                let mut screen = Screen::new();
                for q in day.quads(&gallery) {
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

    for (i, (got, f)) in frames.iter().zip(want_frames).enumerate() {
        let want: Frame = (
            f.get("booth").str().into(),
            f.get("border").str().into(),
            f.get("card") == &Json::Bool(true),
            f.get("card_y").float(),
            f.get("shown").num().unwrap() as usize,
            f.get("button").str().into(),
        );
        assert_eq!(got, &want, "frame {}", i + 1);
    }
    let GameScreen::Day(day) = game.screen() else { unreachable!() };
    assert_eq!(day.start_intro().map(i64::from), timeline.get("start_intro").num(), "the frame of start-intro");

    // The sounds: the reference lists one entry per letter's text-reveal;
    // a frame counts once here (no frame has two letters at 0.04 s each).
    let mut want_sounds: Vec<(i64, String)> =
        timeline.get("sounds").list().iter().map(|s| (s.get("frame").num().unwrap(), s.get("id").str().to_string())).collect();
    want_sounds.sort();
    want_sounds.dedup();
    sounds.sort();
    assert_eq!(sounds, want_sounds, "the frames the sounds start on");
    eprintln!("{} frames, {} sound starts, start-intro on frame {:?}: as the reference", frames.len(), sounds.len(), day.start_intro());
}
