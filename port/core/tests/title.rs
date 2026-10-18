//! Compares the title screen the core draws with the Python reference's,
//! byte for byte (milestone 1b). Needs two gitignored, game-derived inputs;
//! with either missing the test says so and passes without checking:
//!
//!     python -I scripts/build_assets/build_pack.py          -> build/assets/start.pack
//!     python -I scripts/reference/titlescreen.py extracted/art/assets extracted/previews/m1b

use std::path::{Path, PathBuf};

use pp_core::pack::Pack;
use pp_core::pages::Gallery;
use pp_core::raster::Screen;
use pp_core::title;

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

#[test]
fn the_title_matches_the_reference() {
    let pack_path = root().join("build/assets/start.pack");
    let reference = root().join("extracted/previews/m1b/title.rgba");
    let Ok(bytes) = std::fs::read(&pack_path) else {
        eprintln!("SKIPPED: {} not found", pack_path.display());
        return;
    };
    let Ok(want) = std::fs::read(&reference) else {
        eprintln!("SKIPPED: {} not found", reference.display());
        return;
    };
    let gallery = Gallery::from_pack(&Pack::parse(bytes).unwrap()).unwrap();
    let mut screen = Screen::new();
    title::draw(&gallery, &mut screen).unwrap();
    let differing = screen.pixels.iter().zip(&want).filter(|(a, b)| a != b).count();
    assert_eq!(differing, 0, "{differing} bytes differ from the reference");
    eprintln!("the title is identical to the reference");
}
