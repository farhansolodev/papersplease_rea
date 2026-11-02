//! The host's side of the platform (`PlatformSys`, the settings store): the
//! page's `window.ppPlatform` (port/www/index.html) keeps the settings in the
//! browser's local storage and switches the browser's full screen. Outside a
//! browser every call does nothing.

use pp_core::game::Platform;
use pp_core::settings::Saved;

#[cfg(target_arch = "wasm32")]
mod js {
    use js_sys::{Array, Function, Reflect};
    use wasm_bindgen::{JsCast, JsValue};

    pub fn call(method: &str, args: &[JsValue]) -> JsValue {
        let Ok(platform) = Reflect::get(&js_sys::global(), &JsValue::from_str("ppPlatform")) else {
            return JsValue::UNDEFINED;
        };
        if platform.is_undefined() || platform.is_null() {
            return JsValue::UNDEFINED;
        }
        let Ok(f) = Reflect::get(&platform, &JsValue::from_str(method)).and_then(|f| f.dyn_into::<Function>()) else {
            return JsValue::UNDEFINED;
        };
        f.apply(&platform, &args.iter().collect::<Array>()).unwrap_or(JsValue::UNDEFINED)
    }
}

pub struct PagePlatform;

#[cfg(target_arch = "wasm32")]
impl Platform for PagePlatform {
    fn fullscreen(&mut self) -> bool {
        js::call("getFullscreen", &[]).as_bool().unwrap_or(false)
    }

    fn set_fullscreen(&mut self, on: bool) {
        js::call("setFullscreen", &[on.into()]);
    }

    /// Under the names of the game's own settings file
    /// (docs/save-format.md, "Settings").
    fn save_settings(&mut self, saved: &Saved) {
        use js_sys::{Object, Reflect};
        use wasm_bindgen::JsValue;
        let obj = Object::new();
        let set = |k: &str, v: JsValue| {
            let _ = Reflect::set(&obj, &JsValue::from_str(k), &v);
        };
        set("fullscreen", saved.fullscreen.into());
        set("nudity", saved.nudity.into());
        set("easyMode", saved.easy_mode.into());
        set("dateFormatIndex", saved.date_format_index.into());
        set("musicVolume", saved.music_volume.into());
        set("soundVolume", saved.sound_volume.into());
        js::call("saveSettings", &[obj.into()]);
    }
}

#[cfg(not(target_arch = "wasm32"))]
impl Platform for PagePlatform {
    fn fullscreen(&mut self) -> bool {
        false
    }
    fn set_fullscreen(&mut self, _: bool) {}
    fn save_settings(&mut self, _: &Saved) {}
}
