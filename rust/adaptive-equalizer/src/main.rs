use std::env;
use anyhow::Result;
use glium::glutin;
use glium::Surface;
use imgui::Context;
use imgui_glium_renderer::Renderer;
use imgui_winit_support::{HiDpiMode, WinitPlatform};
use std::sync::{Arc, Mutex};
use std::time::Instant;

use crate::gui::windows::EqualizerWindow;
use crate::audio::AudioEngine;

mod audio;
mod gui;

fn main() -> Result<()> {
    // Initialize environment
    env::set_var("RUST_BACKTRACE", "1");
    env_logger::init();

    // Initialize audio engine
    let bands = Arc::new(Mutex::new([0.0f32; 10]));
    let mut audio_engine = AudioEngine::new(bands.clone());
    audio_engine.initialize()?;

    // Create window
    let event_loop = glutin::event_loop::EventLoop::new();
    let wb = glutin::window::WindowBuilder::new()
        .with_title("Adaptive Equalizer")
        .with_inner_size(glutin::dpi::LogicalSize::new(1024.0, 768.0));
    let cb = glutin::ContextBuilder::new()
        .with_vsync(true);
    let display = glium::Display::new(wb, cb, &event_loop)?;

    // Initialize imgui
    let mut imgui = Context::create();
    imgui.set_ini_filename(None);

    // Initialize winit platform
    let mut platform = WinitPlatform::init(&mut imgui);
    platform.attach_window(
        imgui.io_mut(),
        display.gl_window().window(),
        HiDpiMode::Default,
    );

    // Initialize renderer
    let mut renderer = Renderer::init(&mut imgui, &display)?;

    let mut equalizer_window = EqualizerWindow::new(bands);
    let mut last_frame = Instant::now();

    // Main loop
    event_loop.run(move |event, _, control_flow| {
        match event {
            glutin::event::Event::NewEvents(_) => {
                let now = Instant::now();
                imgui.io_mut().update_delta_time(now - last_frame);
                last_frame = now;
            }
            glutin::event::Event::MainEventsCleared => {
                let gl_window = display.gl_window();
                platform
                    .prepare_frame(imgui.io_mut(), gl_window.window())
                    .expect("Failed to prepare frame");
                gl_window.window().request_redraw();
            }
            glutin::event::Event::RedrawRequested(_) => {
                let gl_window = display.gl_window();
                let mut target = display.draw();
                target.clear_color(0.2, 0.2, 0.2, 1.0);

                let ui = imgui.frame();
                platform.prepare_render(&ui, gl_window.window());
                
                equalizer_window.render(&ui);

                let draw_data = imgui.render();
                renderer
                    .render(&mut target, draw_data)
                    .expect("Failed to render");
                
                target.finish().expect("Failed to swap buffers");
            }
            glutin::event::Event::WindowEvent {
                event: glutin::event::WindowEvent::CloseRequested,
                ..
            } => {
                *control_flow = glutin::event_loop::ControlFlow::Exit;
            }
            event => {
                platform.handle_event(
                    imgui.io_mut(),
                    display.gl_window().window(),
                    &event,
                );
            }
        }
    });
}