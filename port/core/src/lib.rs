//! The game core: plain Rust, no Bevy, no browser (docs/DESIGN.md).
//!
//! Milestone 0 holds only what an empty page needs: the screen size and its
//! whole-number fit to a window, the fixed time step, and a test card.

pub mod screen;
pub mod stepper;
pub mod testcard;
