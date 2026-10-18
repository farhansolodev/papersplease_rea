//! The game's screen picture and how it sits in a window.

/// Width of the game's screen picture in game pixels (`Layout.kPixelWidth`,
/// docs/screen-output.md, "The screen picture and the window").
pub const WIDTH: u32 = 570;
/// Height of the game's screen picture in game pixels.
pub const HEIGHT: u32 = 320;

/// Where the screen picture is drawn inside a window, in the window's
/// physical pixels, with (0, 0) at the window's top left.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Fit {
    /// Window pixels per game pixel, always a whole number of at least 1.
    pub zoom: u32,
    /// Left edge of the picture. Negative when the window is narrower than
    /// the picture, in which case the picture is cropped evenly.
    pub x: i32,
    /// Top edge of the picture (negative when the window is shorter).
    pub y: i32,
    /// Picture width in window pixels (`WIDTH * zoom`).
    pub width: u32,
    /// Picture height in window pixels (`HEIGHT * zoom`).
    pub height: u32,
}

/// The largest whole-number zoom at which the picture fits the window, with
/// the picture centred and the rest of the window left black.
///
/// Sizes are physical pixels (what the screen really shows), not the
/// browser's scaled "logical" ones, so a game pixel is always an exact
/// block of screen pixels. A window smaller than the picture gets zoom 1
/// and the picture is cropped.
///
/// The position is rounded down to a whole pixel so the picture never
/// lands between two screen pixels (that would blur or unevenly double
/// rows and columns).
pub fn fit(window_width: u32, window_height: u32) -> Fit {
    let zoom = (window_width / WIDTH).min(window_height / HEIGHT).max(1);
    let width = WIDTH * zoom;
    let height = HEIGHT * zoom;
    Fit {
        zoom,
        x: (window_width as i32 - width as i32).div_euclid(2),
        y: (window_height as i32 - height as i32).div_euclid(2),
        width,
        height,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_multiples_fill_the_window() {
        let f = fit(1140, 640);
        assert_eq!((f.zoom, f.x, f.y, f.width, f.height), (2, 0, 0, 1140, 640));
        let f = fit(570, 320);
        assert_eq!((f.zoom, f.x, f.y), (1, 0, 0));
    }

    #[test]
    fn the_smaller_direction_decides_the_zoom() {
        // 1920 x 1080: width allows 3 (1710), height allows 3 (960).
        let f = fit(1920, 1080);
        assert_eq!((f.zoom, f.x, f.y), (3, 105, 60));
        // Tall narrow window: width allows 1 only.
        assert_eq!(fit(800, 2000).zoom, 1);
        // Wide short window: height allows 1 only.
        assert_eq!(fit(3000, 500).zoom, 1);
    }

    #[test]
    fn the_zoom_never_drops_below_one() {
        let f = fit(300, 200);
        assert_eq!(f.zoom, 1);
        // Cropped evenly: 570 - 300 = 270 -> -135; 320 - 200 = 120 -> -60.
        assert_eq!((f.x, f.y), (-135, -60));
        assert_eq!(fit(0, 0).zoom, 1);
    }

    #[test]
    fn an_odd_margin_rounds_down_to_a_whole_pixel() {
        // 1141 wide: margin 1 -> x 0. 1143 wide: margin 3 -> x 1.
        assert_eq!(fit(1141, 640).x, 0);
        assert_eq!(fit(1143, 640).x, 1);
        // A negative odd margin rounds down too (-1 -> -1, not 0).
        assert_eq!(fit(569, 320).x, -1);
    }

    #[test]
    fn the_picture_always_fits_when_it_can() {
        for w in 570..4000u32 {
            for h in [320u32, 500, 639, 640, 1080, 2160] {
                let f = fit(w, h);
                assert!(f.x >= 0 && f.y >= 0, "{w}x{h}");
                assert!(f.x as u32 + f.width <= w && f.y as u32 + f.height <= h);
                // One more zoom step would not fit.
                assert!(WIDTH * (f.zoom + 1) > w || HEIGHT * (f.zoom + 1) > h);
            }
        }
    }
}
