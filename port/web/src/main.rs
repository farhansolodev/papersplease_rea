//! Milestone 0's host: one Bevy window (in a browser, a canvas) showing the
//! core's 570 x 320 test card at the largest whole-number zoom, on black.

use bevy::asset::RenderAssetUsages;
use bevy::image::ImageSampler;
use bevy::prelude::*;
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};
use bevy::window::PrimaryWindow;
use pp_core::screen::{self, HEIGHT, WIDTH};
use pp_core::stepper::Stepper;
use pp_core::testcard;

/// The time step and the picture, as the host holds them.
#[derive(Resource)]
struct Host {
    stepper: Stepper,
    /// Pictures drawn so far (the yellow number on the test card).
    frames: u64,
    picture: Handle<Image>,
}

/// The sprite that shows the screen picture.
#[derive(Component)]
struct ScreenSprite;

fn main() {
    App::new()
        .add_plugins(DefaultPlugins.set(WindowPlugin {
            primary_window: Some(Window {
                title: "Papers, Please (browser port, milestone 0)".into(),
                canvas: Some("#game".into()),
                fit_canvas_to_parent: true,
                prevent_default_event_handling: true,
                ..default()
            }),
            ..default()
        }))
        .insert_resource(ClearColor(Color::BLACK))
        .add_systems(Startup, setup)
        .add_systems(Update, (step_and_draw, place_picture).chain())
        .run();
}

fn setup(mut commands: Commands, mut images: ResMut<Assets<Image>>) {
    // An sRGB texture: the card's byte values are what the game would
    // store, and the graphics card turns them to light and back on the way
    // to the (sRGB) window, which returns the same bytes.
    let mut image = Image::new_fill(
        Extent3d {
            width: WIDTH,
            height: HEIGHT,
            depth_or_array_layers: 1,
        },
        TextureDimension::D2,
        &[0, 0, 0, 255],
        TextureFormat::Rgba8UnormSrgb,
        RenderAssetUsages::default(),
    );
    // Nearest-pixel reads: the zoom shows blocks, never a blur.
    image.sampler = ImageSampler::nearest();
    let picture = images.add(image);

    commands.spawn(Camera2d);
    commands.spawn((ScreenSprite, Sprite::from_image(picture.clone())));
    commands.insert_resource(Host {
        stepper: Stepper::new(),
        frames: 0,
        picture,
    });
}

/// Runs the core's 1/60 s steps that real time asks for, then draws the card.
fn step_and_draw(time: Res<Time<Real>>, mut host: ResMut<Host>, mut images: ResMut<Assets<Image>>) {
    let nanos = time.delta().as_nanos().min(u64::MAX as u128) as u64;
    host.stepper.advance(nanos);
    host.frames += 1;
    let (steps, frames) = (host.stepper.steps(), host.frames);
    if let Some(mut image) = images.get_mut(&host.picture) {
        if let Some(data) = image.data.as_mut() {
            testcard::render(steps, frames, data);
        }
    }
}

/// Sizes and places the sprite for the window's current physical size.
fn place_picture(
    window: Single<&Window, With<PrimaryWindow>>,
    mut sprite: Single<(&mut Sprite, &mut Transform), With<ScreenSprite>>,
) {
    let (w, h) = (window.physical_width(), window.physical_height());
    let scale = window.scale_factor();
    let fit = screen::fit(w, h);
    // The camera's world unit is one logical pixel (`scale` physical
    // ones). Work in physical pixels and divide once at the end.
    let centre_x = fit.x as f32 + fit.width as f32 / 2.0 - w as f32 / 2.0;
    let centre_y = fit.y as f32 + fit.height as f32 / 2.0 - h as f32 / 2.0;
    sprite.0.custom_size = Some(Vec2::new(fit.width as f32, fit.height as f32) / scale);
    sprite.1.translation = Vec3::new(centre_x / scale, -centre_y / scale, 0.0);
}
