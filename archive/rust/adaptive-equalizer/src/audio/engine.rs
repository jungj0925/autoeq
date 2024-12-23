use anyhow::Result;
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use std::sync::{Arc, Mutex};
use log::{info};
use super::wasapi::WasapiCapture;
use super::equalizer::Equalizer;

pub struct AudioEngine {
    bands: Arc<Mutex<[f32; 10]>>,
    wasapi_capture: WasapiCapture,
    sample_rate: f32,
}

impl AudioEngine {
    pub fn new(bands: Arc<Mutex<[f32; 10]>>) -> Self {
        Self {
            bands,
            wasapi_capture: WasapiCapture::new().expect("Failed to create WASAPI capture"),
            sample_rate: 44100.0,
        }
    }

    pub fn initialize(&mut self) -> Result<()> {
        info!("Initializing audio engine");
        Ok(())
    }

    pub fn process_audio(&mut self) -> Result<()> {
        let mut input_data = self.wasapi_capture.capture_data()?;
        let mut bands = self.bands.lock().unwrap();
        let equalizer = Equalizer::new(bands.len());

        equalizer.process(&mut input_data);
        info!("Processed audio data: {:?}", input_data);

        Ok(())
    }
} 