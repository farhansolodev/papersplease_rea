//! The game's random generator, `app.Rand` (docs/rand.md), and the shuffled
//! order `app.ShuffledSequence` without its reshuffling (docs/traveler-build.md,
//! "Shuffled sequences"). The same as scripts/reference/rand.py and
//! cyclers.py. Milestone 3a needs them for `Sounds.xml`, whose sounds with
//! several recordings each draw from one generator when the file is read.

/// `app.Rand`: the published "sfc32" mixing step with the game's own seeding.
#[derive(Debug, Clone)]
pub struct Rand {
    a: u32,
    b: u32,
    c: u32,
    d: u32,
}

impl Rand {
    pub fn new(seed: i32) -> Rand {
        let mut r = Rand { a: 0x36AE_F51A, b: 0x21D4_B3EB, c: 0xF251_7ABF, d: seed as u32 };
        for _ in 0..15 {
            r.next_int();
        }
        r
    }

    /// The next value, 0 to 2^31 - 1.
    pub fn next_int(&mut self) -> i32 {
        let result = self.a.wrapping_add(self.b).wrapping_add(self.d);
        self.d = self.d.wrapping_add(1);
        self.a = self.b ^ (self.b >> 9);
        self.b = self.c.wrapping_mul(9);
        self.c = self.c.rotate_left(21).wrapping_add(result);
        (result & 0x7FFF_FFFF) as i32
    }

    /// The next value, 0.0 to 1.0, both included (`nextFloat`, `random`).
    pub fn next_float(&mut self) -> f64 {
        self.next_int() as f64 / 2_147_483_647.0
    }
}

/// `app.ArrayUtil.makeShuffled`: 0..count in a shuffled order, one draw each.
fn make_shuffled(rand: &mut Rand, count: usize) -> Vec<usize> {
    let mut array: Vec<usize> = (0..count).collect();
    for i in 0..count {
        let n = count - i;
        let j = (rand.next_float() * n as f64) as usize;
        if j < array.len() {
            array.swap(n - 1, j);
        } else {
            // Only when the draw is exactly 1.0 on the first step: the Haxe
            // array reads nothing and grows by one (cyclers.py; not checked
            // in this build).
            let last = array[n - 1];
            array[n - 1] = 0;
            array.push(last);
        }
    }
    array
}

/// `app.ShuffledSequence` with no reshuffling: hands out a shuffled order of
/// 0..count, then starts it again.
#[derive(Debug, Clone)]
pub struct ShuffledSequence {
    array: Vec<usize>,
    cur: usize,
}

impl ShuffledSequence {
    pub fn new(count: usize, seed: i32) -> ShuffledSequence {
        ShuffledSequence { array: make_shuffled(&mut Rand::new(seed), count), cur: 0 }
    }

    pub fn next(&mut self) -> usize {
        if self.cur >= self.array.len() {
            self.cur = 0;
        }
        let value = self.array[self.cur];
        self.cur += 1;
        value
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn matches_the_reference_generator() {
        // python -I scripts/reference/rand.py 5 0 23 -1
        let cases: [(i32, [i32; 5]); 3] = [
            (0, [447463269, 2055511169, 1798894853, 1039853963, 1067824076]),
            (23, [1000321259, 74231484, 935348709, 1580549928, 607499174]),
            (-1, [89931407, 1807315563, 1092430541, 1187047259, 257213716]),
        ];
        for (seed, values) in cases {
            let mut r = Rand::new(seed);
            let got: Vec<i32> = (0..5).map(|_| r.next_int()).collect();
            assert_eq!(got, values, "seed {seed}");
        }
    }

    #[test]
    fn shuffled_orders_match_the_reference() {
        // cyclers.ShuffledSequence(count, seed), first values.
        let take = |count, seed, n| {
            let mut s = ShuffledSequence::new(count, seed);
            (0..n).map(|_| s.next()).collect::<Vec<_>>()
        };
        assert_eq!(take(3, 1, 6), [0, 2, 1, 0, 2, 1]);
        assert_eq!(take(3, 99, 3), [2, 1, 0]);
        assert_eq!(take(10, 77, 10), [2, 8, 1, 6, 3, 4, 5, 9, 0, 7]);
    }
}
