//! The fixed time step: the core always moves in steps of 1/60 s, however
//! often the browser calls the page (docs/DESIGN.md, decision 1; the
//! original's rule is in docs/border-view.md, "The frame rate").

/// Nanoseconds in one second, times the steps per second: the accumulator
/// counts in nanoseconds x 60 so that a step is a whole number of units
/// (1/60 s is not a whole number of nanoseconds).
const UNITS_PER_STEP: u64 = 1_000_000_000;
const STEPS_PER_SECOND: u64 = 60;

/// The longest real time one call counts, as the original caps a frame at
/// 0.1 s. After a long pause (a hidden tab) the game catches up by at most
/// 6 steps instead of thousands.
pub const MAX_FRAME_NANOS: u64 = 100_000_000;

/// Turns real elapsed time into a number of 1/60 s steps, keeping the
/// remainder for the next call. Integer arithmetic only, so it never drifts.
#[derive(Debug, Default, Clone)]
pub struct Stepper {
    accumulated: u64,
    steps: u64,
}

impl Stepper {
    pub fn new() -> Self {
        Self::default()
    }

    /// Adds `elapsed_nanos` of real time (at most [`MAX_FRAME_NANOS`] of it
    /// counts) and returns how many steps to run now.
    pub fn advance(&mut self, elapsed_nanos: u64) -> u32 {
        self.accumulated += elapsed_nanos.min(MAX_FRAME_NANOS) * STEPS_PER_SECOND;
        let due = self.accumulated / UNITS_PER_STEP;
        self.accumulated %= UNITS_PER_STEP;
        self.steps += due;
        due as u32
    }

    /// Steps run so far.
    pub fn steps(&self) -> u64 {
        self.steps
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run(frame_nanos: &[u64]) -> u64 {
        let mut s = Stepper::new();
        for &n in frame_nanos {
            s.advance(n);
        }
        s.steps()
    }

    #[test]
    fn sixty_hertz_frames_give_one_step_each() {
        // 1/60 s = 16_666_666.67 ns: frames of 16_666_667 ns drift by a
        // fraction of a unit per frame, so 600 frames give 600 steps.
        let mut s = Stepper::new();
        let mut per_frame = Vec::new();
        for _ in 0..600 {
            per_frame.push(s.advance(16_666_667));
        }
        assert_eq!(s.steps(), 600);
        assert!(per_frame.iter().all(|&n| n <= 1));
    }

    #[test]
    fn a_fast_display_steps_every_few_frames_without_drift() {
        // 144 Hz for exactly one second of frames of 1e9/144 ns.
        let frames: Vec<u64> = (0..144).map(|_| 1_000_000_000 / 144).collect();
        let steps = run(&frames);
        assert!((59..=60).contains(&steps), "{steps}");
        // Ten seconds: within one step of 600.
        let frames: Vec<u64> = (0..1440).map(|_| 1_000_000_000 / 144).collect();
        assert!((599..=600).contains(&run(&frames)));
    }

    #[test]
    fn the_remainder_is_kept() {
        let mut s = Stepper::new();
        // Three calls of a third of a step: nothing, nothing, then one.
        let third = 1_000_000_000 / 60 / 3 + 1;
        assert_eq!(s.advance(third), 0);
        assert_eq!(s.advance(third), 0);
        assert_eq!(s.advance(third), 1);
    }

    #[test]
    fn a_long_pause_is_capped_at_a_tenth_of_a_second() {
        let mut s = Stepper::new();
        assert_eq!(s.advance(60_000_000_000), 6);
        assert_eq!(s.steps(), 6);
        // Never more than 6 in one call, whatever the remainder.
        let mut s = Stepper::new();
        for _ in 0..1000 {
            assert!(s.advance(u64::MAX / 100) <= 6);
        }
    }

    #[test]
    fn no_time_means_no_steps() {
        assert_eq!(Stepper::new().advance(0), 0);
    }
}
