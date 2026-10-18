//! Compares every font page the core draws with the Python reference's, byte
//! for byte (milestone 1a). Needs two gitignored, game-derived inputs; with
//! either missing the test says so and passes without checking:
//!
//!     python -I scripts/build_assets/build_pack.py          -> build/assets/start.pack
//!     python -I scripts/reference/fontpage.py extracted/art/assets extracted/previews/m1

use std::path::{Path, PathBuf};

use pp_core::pack::Pack;
use pp_core::pages::Gallery;
use pp_core::raster::Screen;

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

#[test]
fn every_page_matches_the_reference() {
    let pack_path = root().join("build/assets/start.pack");
    let reference = root().join("extracted/previews/m1");
    let Ok(bytes) = std::fs::read(&pack_path) else {
        eprintln!("SKIPPED: {} not found", pack_path.display());
        return;
    };
    if !reference.join("pages.json").exists() {
        eprintln!("SKIPPED: {} not found", reference.display());
        return;
    }
    let gallery = Gallery::from_pack(&Pack::parse(bytes).unwrap()).unwrap();
    let pages = gallery.pages();
    let mut screen = Screen::new();
    let mut bad = Vec::new();
    for i in 0..pages.len() {
        gallery.draw_page(i, &mut screen);
        let want = std::fs::read(reference.join(format!("page_{i:03}.rgba"))).unwrap();
        if screen.pixels != want {
            let differing = screen.pixels.iter().zip(&want).filter(|(a, b)| a != b).count();
            bad.push(format!("page {i} {:?}: {differing} bytes differ", pages[i]));
        }
    }
    assert!(bad.is_empty(), "pages that differ:\n{}", bad.join("\n"));
    eprintln!("{} pages identical to the reference", pages.len());
}
