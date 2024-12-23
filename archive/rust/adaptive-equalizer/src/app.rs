use std::sync::{Arc, Mutex};

pub struct App {
    equalizer_enabled: bool,
    bands: Arc<Mutex<[f32; 10]>>,
}

impl App {
    pub fn new() -> Self {
        Self {
            equalizer_enabled: true,
            bands: Arc::new(Mutex::new([0.0; 10])),
        }
    }

    pub fn get_bands(&self) -> Arc<Mutex<[f32; 10]>> {
        Arc::clone(&self.bands)
    }

    pub fn is_enabled(&self) -> bool {
        self.equalizer_enabled
    }

    pub fn set_enabled(&mut self, enabled: bool) {
        self.equalizer_enabled = enabled;
    }
} 