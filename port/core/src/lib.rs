//! The game core: plain Rust, no Bevy, no browser (docs/DESIGN.md).
//!
//! Milestone 0: the screen size and its whole-number fit to a window, the
//! fixed time step, and a test card. Milestone 1a: the start pack, pictures,
//! fonts, text layout, the software drawing of quads, and the font test
//! pages. Milestone 1b: the title screen as a still. Milestone 2: the
//! effects' ADPCM decoding, the volume rule and the sound test page.
//! Milestone 3a: the random generator, the audio layer (`app.aud`), input,
//! buttons, the drawn cursor and the title screen alive. Milestone 3b: the
//! game's screen changes with their fade, the settings and the settings
//! screen. Milestone 3c: the typing caption, the page player and the intro
//! screen.

pub mod adpcm;
pub mod aud;
pub mod button;
pub mod fade;
pub mod font;
pub mod game;
pub mod input;
pub mod intro;
pub mod num;
pub mod pack;
pub mod pages;
pub mod picture;
pub mod rand;
pub mod raster;
pub mod reveal_text;
pub mod screen;
pub mod settings;
pub mod settings_screen;
pub mod sound;
pub mod soundtest;
pub mod stepper;
pub mod testcard;
pub mod text;
pub mod title;
mod xmlscan;
