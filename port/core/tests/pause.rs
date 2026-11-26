//! The pause screen of milestone 4b: its two pictures against the Python
//! reference (`pausescreen.py`) byte for byte, and a run of the game on
//! day 1 through real key and mouse presses: Escape pauses, MAIN MENU opens
//! the confirm box (drawn as the reference draws it), Escape presses CANCEL,
//! MAIN MENU again and the red MAIN MENU go to the title. Needs two
//! gitignored, game-derived inputs; with either missing the test says so
//! and passes without checking:
//!
//!     python -I scripts/build_assets/build_pack.py          -> build/assets/start.pack
//!     python -I scripts/reference/pausescreen.py extracted/art/assets extracted/previews/m4b

use std::path::{Path, PathBuf};

use pp_core::aud::{AudioHost, SoundDefs};
use pp_core::fade::State;
use pp_core::game::{Game, GameScreen, Platform};
use pp_core::input::{HostInput, Key};
use pp_core::pack::Pack;
use pp_core::pages::Gallery;
use pp_core::pause::PauseScreen;
use pp_core::raster::Screen;
use pp_core::settings::{Saved, Settings};
use pp_core::sound::Category;

const DT: f64 = 1.0 / 60.0;

#[derive(Default)]
struct Audio {
    started: Vec<String>,
    effects_paused: bool,
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
    fn set_category_pause(&mut self, c: Category, paused: bool) {
        if c == Category::Effect {
            self.effects_paused = paused;
        }
    }
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

fn inputs() -> Option<(Gallery, Pack, PathBuf)> {
    let pack_path = root().join("build/assets/start.pack");
    let out = root().join("extracted/previews/m4b");
    let Ok(bytes) = std::fs::read(&pack_path) else {
        eprintln!("SKIPPED: {} not found", pack_path.display());
        return None;
    };
    if !out.join("pause_a.rgba").exists() {
        eprintln!("SKIPPED: {} not found", out.join("pause_a.rgba").display());
        return None;
    }
    let pack = Pack::parse(bytes).unwrap();
    Some((Gallery::from_pack(&pack).unwrap(), pack, out))
}

fn same_as(screen: &Screen, out: &Path, name: &str) {
    let want = std::fs::read(out.join(format!("{name}.rgba"))).unwrap();
    let differing = screen.pixels.iter().zip(&want).filter(|(a, b)| a != b).count();
    assert_eq!(differing, 0, "{name}: {differing} bytes differ from the reference");
    eprintln!("{name} is identical to the reference");
}

#[test]
fn the_pause_screen_matches_the_reference() {
    let Some((mut gallery, _, out)) = inputs() else { return };
    let settings = Settings::new(true, None);
    let mut pause = PauseScreen::new(&mut gallery, &settings).unwrap();
    pause.update(&gallery, &settings, 0.0);
    let mut screen = Screen::new();
    pause.draw(&gallery, &mut screen);
    same_as(&screen, &out, "pause_a");
}

/// Presses for a run: Escape held, the left button held, where the mouse is.
fn input(escape: bool, left: bool, at: (f64, f64)) -> HostInput {
    let mut h = HostInput { mouse_valid: true, mouse: at, left_down: left, ..HostInput::default() };
    h.keys[Key::Escape as usize] = escape;
    h
}

#[test]
fn escape_pauses_and_main_menu_goes_to_the_title() {
    let Some((mut gallery, pack, out)) = inputs() else { return };
    let defs = SoundDefs::parse(std::str::from_utf8(pack.get("data/Sounds.xml").unwrap()).unwrap()).unwrap();
    let mut game = Game::new_day(defs, Settings::new(true, None));
    let (mut audio, mut page) = (Audio::default(), Page);
    let away = (500.0, 300.0);
    let mut step = |game: &mut Game, gallery: &mut Gallery, audio: &mut Audio, h: HostInput| {
        let before = audio.started.len();
        game.step(&h, DT, gallery, audio, &mut page).unwrap();
        audio.started[before..].to_vec()
    };
    let booth = |game: &Game| match game.screen() {
        GameScreen::Day(d) => d.booth_state(),
        _ => "not the day",
    };
    // Up to the booth's `empty`.
    while booth(&game) != "empty" {
        step(&mut game, &mut gallery, &mut audio, input(false, false, away));
    }
    let time = game.time();

    // Escape: paused at once (effects paused, `button-drop`), no game time.
    let started = step(&mut game, &mut gallery, &mut audio, input(true, false, away));
    assert_eq!(game.change_state(), State::Paused);
    assert!(game.pause_screen().is_some() && audio.effects_paused);
    assert!(started.iter().any(|f| f.starts_with("button-drop")), "{started:?}");
    for _ in 0..2 {
        step(&mut game, &mut gallery, &mut audio, input(true, false, away));
    }
    // Let go: the key was masked, so RESUME is not pressed.
    let started = step(&mut game, &mut gallery, &mut audio, input(false, false, away));
    assert!(started.is_empty(), "{started:?}");
    assert_eq!(game.change_state(), State::Paused);
    assert_eq!(game.time(), time, "no game time passes while paused");

    // MAIN MENU (at 220, 270, 129 x 19): the confirm box.
    let main_menu = (284.0, 279.0);
    for left in [true, true, true, false] {
        step(&mut game, &mut gallery, &mut audio, input(false, left, main_menu));
    }
    let p = game.pause_screen().unwrap();
    assert!(p.confirm_shown());
    let mut screen = Screen::new();
    p.draw(&gallery, &mut screen);
    same_as(&screen, &out, "pause_b");

    // Escape presses CANCEL, not RESUME under the box.
    for escape in [true, true, false] {
        step(&mut game, &mut gallery, &mut audio, input(escape, false, away));
    }
    assert!(!game.pause_screen().unwrap().confirm_shown());
    assert_eq!(game.change_state(), State::Paused);

    // MAIN MENU again, then the red MAIN MENU (220, 131): out of the pause
    // (`hover-up`, effects resumed) and the fade to the title.
    for left in [true, true, true, false] {
        step(&mut game, &mut gallery, &mut audio, input(false, left, main_menu));
    }
    let red = (284.0, 140.0);
    for left in [true, true, true] {
        step(&mut game, &mut gallery, &mut audio, input(false, left, red));
    }
    let started = step(&mut game, &mut gallery, &mut audio, input(false, false, red));
    assert!(started.iter().any(|f| f.starts_with("hover-up")), "{started:?}");
    assert!(game.pause_screen().is_none() && !audio.effects_paused);
    assert_eq!(game.change_state(), State::Off);
    let mut frames = 0;
    while !matches!(game.screen(), GameScreen::Title(_)) {
        step(&mut game, &mut gallery, &mut audio, input(false, false, away));
        frames += 1;
        assert!(frames < 200, "no title");
    }
    assert_eq!(frames, 70, "the title is built on the 70th frame after the click");
    eprintln!("paused, the confirm box, CANCEL, MAIN MENU: the title {frames} frames after the click");
}
