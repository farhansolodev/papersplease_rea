//! Small number helpers the game uses (`app.Num`, Haxe's `Math`).

/// Haxe `Math.round` as compiled (docs/fact-pictures.md, checked in the
/// instructions): the whole part toward zero, plus one if the rest is 0.5 or
/// more, minus one if it is below -0.5. So 2.5 gives 3 and -2.5 gives -2.
pub fn math_round(x: f64) -> i32 {
    let i = x as i32;
    let d = x - i as f64;
    if d >= 1.0 || -1.0 >= d {
        i
    } else if d >= 0.5 {
        i + 1
    } else if -0.5 > d {
        i - 1
    } else {
        i
    }
}

/// `app.Num.smoothstep`: 0 below `edge0`, 1 above `edge1`, an S-curve between.
pub fn smoothstep(edge0: f64, edge1: f64, x: f64) -> f64 {
    let t = f64::max(0.0, f64::min(1.0, (x - edge0) / (edge1 - edge0)));
    (3.0 - t * 2.0) * t * t
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rounds_halves_up_and_negative_halves_toward_zero() {
        assert_eq!(math_round(2.5), 3);
        assert_eq!(math_round(2.49), 2);
        assert_eq!(math_round(-2.5), -2);
        assert_eq!(math_round(-2.51), -3);
        assert_eq!(math_round(292.0), 292);
    }

    #[test]
    fn smoothstep_is_held_at_both_ends() {
        assert_eq!(smoothstep(0.0, 0.2, -1.0), 0.0);
        assert_eq!(smoothstep(0.0, 0.2, 0.1), 0.5);
        assert_eq!(smoothstep(0.0, 0.2, 5.0), 1.0);
    }
}
