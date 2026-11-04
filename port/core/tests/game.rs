//! Drives the game frame by frame (milestone 3b): the title's settings
//! button, the fade, the settings screen, its buttons and volume bar, the
//! settings applied and saved, Escape back to a title that does not rise.
//! Needs the gitignored start pack; without it the test says so and passes:
//!
//!     python -I scripts/build_assets/build_pack.py          -> build/assets/start.pack

use std::path::Path;

use pp_core::aud::{AudioHost, SoundDefs};
use pp_core::fade::State;
use pp_core::game::{Game, GameScreen, Platform};
use pp_core::input::{HostInput, Key};
use pp_core::pack::Pack;
use pp_core::pages::Gallery;
use pp_core::settings::{Saved, Settings};
use pp_core::sound::Category;

const DT: f64 = 1.0 / 60.0;

#[derive(Default)]
struct Audio {
    started: Vec<String>,
    volumes: Vec<(Category, f32)>,
}

impl AudioHost for Audio {
    fn start(&mut self, _: u32, _: Category, file: &str, _: bool, _: f32) {
        self.started.push(file.to_string());
    }
    fn stop(&mut self, _: u32) {}
    fn set_volume(&mut self, _: u32, _: f32) {}
    /// Every sound plays on (the song never ends here).
    fn position(&mut self, _: u32) -> f64 {
        1.0
    }
    fn set_category_pause(&mut self, _: Category, _: bool) {}
    fn set_category_volume(&mut self, category: Category, volume: f32) {
        self.volumes.push((category, volume));
    }
}

#[derive(Default)]
struct Page {
    fullscreen: bool,
    saved: Vec<Saved>,
}

impl Platform for Page {
    fn fullscreen(&mut self) -> bool {
        self.fullscreen
    }
    fn set_fullscreen(&mut self, on: bool) {
        self.fullscreen = on;
    }
    fn save_settings(&mut self, saved: &Saved) {
        self.saved.push(*saved);
    }
}

struct Rig {
    gallery: Gallery,
    game: Game,
    audio: Audio,
    page: Page,
    host: HostInput,
}

impl Rig {
    fn frames(&mut self, n: usize) {
        for _ in 0..n {
            self.game.step(&self.host, DT, &mut self.gallery, &mut self.audio, &mut self.page).unwrap();
        }
    }

    fn mouse(&mut self, x: f64, y: f64, down: bool) {
        (self.host.mouse_valid, self.host.mouse, self.host.left_down) = (true, (x, y), down);
        self.frames(1);
    }

    fn click(&mut self, x: f64, y: f64) {
        self.mouse(x, y, true);
        self.mouse(x, y, false);
    }

    fn screen(&self) -> &'static str {
        match self.game.screen() {
            GameScreen::Title(_) => "title",
            GameScreen::Settings(_) => "settings",
            GameScreen::Intro(_) => "intro",
            GameScreen::Day(_) => "day",
            GameScreen::Empty => "empty",
        }
    }
}

#[test]
fn title_to_settings_and_back() {
    let pack_path = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../build/assets/start.pack");
    let Ok(bytes) = std::fs::read(&pack_path) else {
        eprintln!("SKIPPED: {} not found", pack_path.display());
        return;
    };
    let pack = Pack::parse(bytes).unwrap();
    let gallery = Gallery::from_pack(&pack).unwrap();
    let defs = SoundDefs::parse(std::str::from_utf8(pack.get("data/Sounds.xml").unwrap()).unwrap()).unwrap();
    let mut audio = Audio::default();
    let game = Game::new(&gallery, defs, Settings::new(true, None), &mut audio).unwrap();
    let mut r = Rig { gallery, game, audio, page: Page::default(), host: HostInput::default() };

    // The first frame applies the settings: both gains 1, saved once.
    r.frames(1);
    assert_eq!(r.audio.volumes, [(Category::Music, 1.0), (Category::Effect, 1.0)]);
    assert_eq!(r.page.saved.len(), 1);
    assert_eq!(r.audio.started, ["Theme.ogg"]);

    // Skip the rise, then the settings button (29 x 29 at 10, 281).
    r.click(300.0, 100.0);
    r.frames(2);
    r.click(24.0, 295.0);
    assert_eq!(r.game.change_state(), State::Off);
    // The change comes on the 70th frame after the click.
    r.frames(69);
    assert_eq!(r.screen(), "title");
    r.frames(1);
    assert_eq!(r.screen(), "settings");
    assert_eq!(r.game.fade(), 1.0);
    r.frames(9);
    assert_eq!(r.game.fade(), 0.0);
    assert_eq!(r.audio.started.iter().filter(|f| *f == "Theme.ogg").count(), 1, "Theme plays on");

    // Music plus at full volume changes nothing; minus gives 0.9, applied
    // squared and saved on the same frame.
    let saves = r.page.saved.len();
    r.click(384.0, 205.0);
    assert_eq!(r.page.saved.len(), saves, "plus at 1.0 changes nothing");
    r.click(365.0, 205.0);
    assert_eq!(r.game.settings.music_volume(), 0.9);
    assert_eq!(r.audio.volumes.last(), Some(&(Category::Effect, 1.0)));
    assert!(r.audio.volumes.contains(&(Category::Music, (0.9f64 * 0.9) as f32)));
    assert_eq!(r.page.saved.last().unwrap().music_volume, 0.9);

    // The Sound bar (level 46 x 12 at 306, 219): held down a fifth of the
    // way along, then dragged past its left end while still held.
    r.mouse(306.0 + 46.0 * 0.2, 225.0, true);
    assert_eq!(r.game.settings.sound_volume(), 0.2);
    r.mouse(250.0, 225.0, true);
    assert_eq!(r.game.settings.sound_volume(), 0.0, "the bar keeps the pointer while it is held");
    r.mouse(250.0, 225.0, false);

    // Fullscreen ticked: the window follows; the window left: the box follows.
    r.click(365.0, 129.0);
    assert!(r.page.fullscreen);
    r.page.fullscreen = false;
    r.frames(2);
    assert!(!r.game.settings.fullscreen());

    // Escape presses DONE on release: back to a title that does not rise.
    r.host.keys[Key::Escape as usize] = true;
    r.frames(3);
    r.host.keys[Key::Escape as usize] = false;
    r.frames(1);
    assert_eq!(r.game.change_state(), State::Off);
    r.frames(70);
    assert_eq!(r.screen(), "title");
    r.frames(2);
    match r.game.screen() {
        GameScreen::Title(t) => assert!(!t.rising(), "a second title does not rise"),
        _ => unreachable!(),
    }
}
