//! The host's side of sound: hands the game's commands to the page's sound
//! player (`window.ppAudio`, port/www/audio.js), which plays them with the
//! browser's Web Audio. Outside a browser every call does nothing.

use pp_core::aud::AudioHost;
use pp_core::sound::Category;

#[cfg(target_arch = "wasm32")]
mod js {
    use js_sys::{Array, Function, Reflect};
    use wasm_bindgen::{JsCast, JsValue};

    pub fn call(method: &str, args: &[JsValue]) -> JsValue {
        let Ok(player) = Reflect::get(&js_sys::global(), &JsValue::from_str("ppAudio")) else {
            return JsValue::UNDEFINED;
        };
        if player.is_undefined() || player.is_null() {
            return JsValue::UNDEFINED;
        }
        let Ok(f) = Reflect::get(&player, &JsValue::from_str(method)).and_then(|f| f.dyn_into::<Function>()) else {
            return JsValue::UNDEFINED;
        };
        f.apply(&player, &args.iter().collect::<Array>()).unwrap_or(JsValue::UNDEFINED)
    }
}

/// The sound player, with the play ids the game hands out (1, 2, 3... for
/// the whole run; docs/audio-layer.md).
pub struct Player {
    next_id: u32,
}

impl Player {
    pub fn new() -> Player {
        Player { next_id: 0 }
    }

    /// The next play id.
    pub fn new_id(&mut self) -> u32 {
        self.next_id += 1;
        self.next_id
    }

    /// Starts a sound; false when the player did not (unknown file, or 32
    /// already playing). The game itself is never told (as in the original).
    #[cfg(target_arch = "wasm32")]
    pub fn start(&self, id: u32, category: Category, file: &str, looping: bool, volume: f64) -> bool {
        use wasm_bindgen::JsValue;
        js::call(
            "start",
            &[
                JsValue::from(id),
                JsValue::from(category as u32),
                JsValue::from_str(file),
                JsValue::from_bool(looping),
                JsValue::from_f64(volume),
            ],
        )
        .as_bool()
        .unwrap_or(false)
    }

    #[cfg(target_arch = "wasm32")]
    pub fn stop(&self, id: u32) {
        js::call("stop", &[id.into()]);
    }

    #[cfg(target_arch = "wasm32")]
    pub fn set_volume(&self, id: u32, volume: f64) {
        js::call("setVolume", &[id.into(), volume.into()]);
    }

    /// The sound's position in seconds, or -1 when the player does not have it.
    #[cfg(target_arch = "wasm32")]
    pub fn position(&self, id: u32) -> f64 {
        js::call("position", &[id.into()]).as_f64().unwrap_or(-1.0)
    }

    #[cfg(target_arch = "wasm32")]
    pub fn set_category_pause(&self, category: Category, paused: bool) {
        js::call("setCategoryPause", &[(category as u32).into(), paused.into()]);
    }

    #[cfg(target_arch = "wasm32")]
    pub fn set_category_volume(&self, category: Category, volume: f64) {
        js::call("setCategoryVolume", &[(category as u32).into(), volume.into()]);
    }

    /// Once a frame: the player frees finished one-shots.
    #[cfg(target_arch = "wasm32")]
    pub fn update(&self) {
        js::call("update", &[]);
    }

    /// Hands a decoded effect to the player.
    #[cfg(target_arch = "wasm32")]
    pub fn add_clip(&self, clip: &pp_core::adpcm::Clip) {
        use wasm_bindgen::JsValue;
        let samples = js_sys::Int16Array::from(clip.samples.as_slice());
        js::call(
            "addClip",
            &[JsValue::from_str(&clip.name), clip.channels.into(), clip.rate.into(), samples.into()],
        );
    }

    #[cfg(not(target_arch = "wasm32"))]
    pub fn start(&self, _: u32, _: Category, _: &str, _: bool, _: f64) -> bool {
        false
    }
    #[cfg(not(target_arch = "wasm32"))]
    pub fn stop(&self, _: u32) {}
    #[cfg(not(target_arch = "wasm32"))]
    pub fn set_volume(&self, _: u32, _: f64) {}
    #[cfg(not(target_arch = "wasm32"))]
    pub fn position(&self, _: u32) -> f64 {
        -1.0
    }
    #[cfg(not(target_arch = "wasm32"))]
    pub fn set_category_pause(&self, _: Category, _: bool) {}
    #[cfg(not(target_arch = "wasm32"))]
    pub fn set_category_volume(&self, _: Category, _: f64) {}
    #[cfg(not(target_arch = "wasm32"))]
    pub fn update(&self) {}
    #[cfg(not(target_arch = "wasm32"))]
    pub fn add_clip(&self, _: &pp_core::adpcm::Clip) {}
}

/// The game's audio layer (`pp_core::aud`) talks to the player through this,
/// as the original's talks to `UnityPlatformAudio`. The volume crosses as a
/// 4-byte float, as in the original.
impl AudioHost for Player {
    fn start(&mut self, id: u32, category: Category, file: &str, looping: bool, volume: f32) {
        Player::start(self, id, category, file, looping, volume as f64);
    }
    fn stop(&mut self, id: u32) {
        Player::stop(self, id);
    }
    fn set_volume(&mut self, id: u32, volume: f32) {
        Player::set_volume(self, id, volume as f64);
    }
    fn position(&mut self, id: u32) -> f64 {
        Player::position(self, id)
    }
    fn set_category_pause(&mut self, category: Category, paused: bool) {
        Player::set_category_pause(self, category, paused);
    }
}

/// The effects pack, once the page has downloaded it (`ppConfig.effects`);
/// taken only once, the page's copy is then dropped.
#[cfg(target_arch = "wasm32")]
pub fn take_effects_pack() -> Option<Vec<u8>> {
    use js_sys::{Reflect, Uint8Array};
    use wasm_bindgen::{JsCast, JsValue};
    let cfg = Reflect::get(&js_sys::global(), &JsValue::from_str("ppConfig")).ok()?;
    let bytes = Reflect::get(&cfg, &JsValue::from_str("effects")).ok()?.dyn_into::<Uint8Array>().ok()?;
    let _ = Reflect::set(&cfg, &JsValue::from_str("effects"), &JsValue::NULL);
    Some(bytes.to_vec())
}

#[cfg(not(target_arch = "wasm32"))]
pub fn take_effects_pack() -> Option<Vec<u8>> {
    None
}
