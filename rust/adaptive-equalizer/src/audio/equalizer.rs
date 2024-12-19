pub struct Equalizer {
    bands: [f32; 10],
    sample_rate: f32,
}

impl Equalizer {
    pub fn new(sample_rate: f32) -> Self {
        Self {
            bands: [0.0; 10],
            sample_rate,
        }
    }

    pub fn process(&mut self, input: &[f32], output: &mut [f32]) {
        // We'll implement the actual DSP later
        output.copy_from_slice(input);
    }
} 