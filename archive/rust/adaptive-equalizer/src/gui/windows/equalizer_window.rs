use imgui::*;
use std::sync::{Arc, Mutex};

pub struct EqualizerWindow {
    bands: Arc<Mutex<[f32; 10]>>,
}

impl EqualizerWindow {
    pub fn new(bands: Arc<Mutex<[f32; 10]>>) -> Self {
        Self { bands }
    }

    pub fn render(&mut self, ui: &Ui) {
        ui.window("Equalizer")
            .size([400.0, 300.0], Condition::FirstUseEver)
            .build(|| {
                if let Ok(mut bands) = self.bands.lock() {
                    for i in 0..10 {
                        let freq = 32.0 * (2.0_f32.powi(i as i32));
                        let label = format!("{:.0}Hz", freq);
                        let token = ui.push_id(&label);
                        let mut band_value = bands[i];

                        if ui.slider_config("##v", -12.0f32, 12.0f32)
                            .display_format("%.1f dB")
                            .build(&mut band_value)
                        {
                            bands[i] = band_value;
                        }

                        ui.text(&label);
                        token.pop();

                        if i < 9 {
                            ui.same_line();
                            ui.dummy([20.0, 1.0]);
                            ui.same_line();
                        }
                    }
                }
            });
    }
}