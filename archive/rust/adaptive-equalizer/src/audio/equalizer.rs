use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Write};

pub struct Equalizer {
    bands: Vec<f32>,
    presets: HashMap<String, Vec<f32>>,
}

impl Equalizer {
    pub fn new(num_bands: usize) -> Self {
        Self {
            bands: vec![0.0; num_bands],
            presets: HashMap::new(),
        }
    }

    pub fn set_band_gain(&mut self, band: usize, gain: f32) {
        if band < self.bands.len() {
            self.bands[band] = gain;
        }
    }

    pub fn save_preset(&mut self, name: String) {
        self.presets.insert(name.clone(), self.bands.clone());
        self.write_preset_to_file(name);
    }

    pub fn load_preset(&mut self, name: &str) {
        if let Some(preset) = self.presets.get(name) {
            self.bands = preset.clone();
        }
    }

    fn write_preset_to_file(&self, name: String) {
        let file_name = format!("{}.txt", name);
        let mut file = File::create(file_name).expect("Unable to create file");
        for &gain in &self.bands {
            writeln!(file, "{}", gain).expect("Unable to write data");
        }
    }

    pub fn process(&self, input: &mut [f32]) {
        for sample in input.iter_mut() {
            *sample *= 10.0f32.powf(self.bands.iter().sum::<f32>() / 20.0);
        }
    }
} 