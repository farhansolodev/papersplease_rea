//! The game core: plain Rust, no Bevy, no browser (docs/DESIGN.md).
//!
//! Milestone 0: the screen size and its whole-number fit to a window, the
//! fixed time step, and a test card. Milestone 1a: the start pack, pictures,
//! fonts, text layout, the software drawing of quads, and the font test
//! pages.

pub mod font;
pub mod pack;
pub mod pages;
pub mod picture;
pub mod raster;
pub mod screen;
pub mod stepper;
pub mod testcard;
pub mod text;
mod xmlscan;
