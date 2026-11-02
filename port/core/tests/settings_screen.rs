//! Compares the settings screen the core draws with the Python reference's,
//! byte for byte (milestone 3b), for the two cases the reference draws.
//! Needs two gitignored, game-derived inputs; with either missing the test
//! says so and passes without checking:
//!
//!     python -I scripts/build_assets/build_pack.py          -> build/assets/start.pack
//!     python -I scripts/reference/settingsscreen.py extracted/art/assets extracted/previews/m3b

use std::path::{Path, PathBuf};

use pp_core::pack::Pack;
use pp_core::pages::Gallery;
use pp_core::raster::Screen;
use pp_core::settings::{Saved, Settings};
use pp_core::settings_screen::SettingsScreen;

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn compare(name: &str, saved: Option<Saved>, tip: bool) {
    let pack_path = root().join("build/assets/start.pack");
    let reference = root().join(format!("extracted/previews/m3b/{name}.rgba"));
    let Ok(bytes) = std::fs::read(&pack_path) else {
        eprintln!("SKIPPED: {} not found", pack_path.display());
        return;
    };
    let Ok(want) = std::fs::read(&reference) else {
        eprintln!("SKIPPED: {} not found", reference.display());
        return;
    };
    let mut gallery = Gallery::from_pack(&Pack::parse(bytes).unwrap()).unwrap();
    // A desktop game starts with nudity on.
    let settings = Settings::new(true, saved.as_ref());
    let mut screen = SettingsScreen::new(&mut gallery, &settings).unwrap();
    // The first frame's update shows the settings; the tip as in the 3
    // seconds after easy mode was switched on.
    if tip {
        screen.show_easy_tip(0.0);
    }
    screen.update(&gallery, &settings, 0.0);
    let mut out = Screen::new();
    for q in screen.quads(&gallery) {
        out.draw(&q, &gallery.pictures);
    }
    let differing = out.pixels.iter().zip(&want).filter(|(a, b)| a != b).count();
    assert_eq!(differing, 0, "{name}: {differing} bytes differ from the reference");
    eprintln!("{name} is identical to the reference");
}

#[test]
fn a_new_players_settings_match_the_reference() {
    compare("settings_a", None, false);
}

#[test]
fn changed_settings_and_the_easy_tip_match_the_reference() {
    let saved = Saved {
        fullscreen: true,
        nudity: false,
        easy_mode: true,
        date_format_index: 2,
        music_volume: 0.3,
        sound_volume: 0.7,
    };
    compare("settings_b", Some(saved), true);
}
