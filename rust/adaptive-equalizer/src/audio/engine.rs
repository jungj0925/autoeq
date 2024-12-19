use anyhow::Result;
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use std::sync::{Arc, Mutex};
use ringbuf::HeapRb;
use log::{info, warn, error, debug};

pub struct AudioEngine {
    bands: Arc<Mutex<[f32; 10]>>,
    enabled: bool,
    input_stream: Option<cpal::Stream>,
    output_stream: Option<cpal::Stream>,
    sample_rate: f32,
}

impl AudioEngine {
    pub fn new(bands: Arc<Mutex<[f32; 10]>>) -> Self {
        Self {
            bands,
            enabled: true,
            input_stream: None,
            output_stream: None,
            sample_rate: 44100.0,
        }
    }

    pub fn initialize(&mut self) -> Result<()> {
        info!("Initializing audio engine");
        let host = cpal::default_host();
        
        // Get default devices
        let input_device = host.default_input_device()
            .ok_or_else(|| anyhow::anyhow!("No input device found"))?;
        let output_device = host.default_output_device()
            .ok_or_else(|| anyhow::anyhow!("No output device found"))?;

        info!("Using input device: {}", input_device.name()?);
        info!("Using output device: {}", output_device.name()?);

        // Get supported configs
        let supported_config = input_device.default_input_config()?;
        self.sample_rate = supported_config.sample_rate().0 as f32;
        info!("Sample rate: {}", self.sample_rate);

        // Create ring buffer for audio data
        let buffer_size = 4096;
        info!("Creating ring buffer with size: {}", buffer_size);
        let ring_buffer = HeapRb::new(buffer_size);
        let (producer, consumer) = ring_buffer.split();

        // Create streams
        info!("Building input stream");
        let input_stream = self.build_input_stream(input_device, producer)?;
        
        info!("Building output stream");
        let output_stream = self.build_output_stream(output_device, consumer)?;

        // Play streams
        info!("Starting audio streams");
        input_stream.play()?;
        output_stream.play()?;

        self.input_stream = Some(input_stream);
        self.output_stream = Some(output_stream);

        info!("Audio engine initialized successfully");
        Ok(())
    }

    fn build_input_stream(
        &self,
        device: cpal::Device,
        mut producer: ringbuf::Producer<f32, Arc<HeapRb<f32>>>,
    ) -> Result<cpal::Stream> {
        let config = device.default_input_config()?;
        info!("Input config: {:?}", config);
        
        let input_data_fn = move |data: &[f32], _: &cpal::InputCallbackInfo| {
            debug!("Input callback with {} samples", data.len());
            
            if data.is_empty() {
                return;
            }

            let mut write_pos = 0;
            while write_pos < data.len() {
                let remaining = data.len() - write_pos;
                let chunk_size = remaining.min(256); // Process smaller chunks
                
                if let Some(chunk) = data.get(write_pos..write_pos + chunk_size) {
                    let written = producer.push_slice(chunk);
                    if written == 0 {
                        warn!("Input buffer full");
                        break;
                    }
                    write_pos += written;
                } else {
                    error!("Invalid chunk indices: {} to {}", write_pos, write_pos + chunk_size);
                    break;
                }
            }
        };

        device.build_input_stream(
            &config.into(),
            input_data_fn,
            |err| error!("Error in input stream: {}", err),
            None,
        ).map_err(Into::into)
    }

    fn build_output_stream(
        &self,
        device: cpal::Device,
        mut consumer: ringbuf::Consumer<f32, Arc<HeapRb<f32>>>,
    ) -> Result<cpal::Stream> {
        let config = device.default_output_config()?;
        info!("Output config: {:?}", config);
        let bands = self.bands.clone();
        
        let output_data_fn = move |data: &mut [f32], _: &cpal::OutputCallbackInfo| {
            debug!("Output callback with {} samples", data.len());
            
            if data.is_empty() {
                return;
            }

            let mut read_pos = 0;
            while read_pos < data.len() {
                let remaining = data.len() - read_pos;
                let chunk_size = remaining.min(256); // Process smaller chunks
                
                if let Some(chunk) = data.get_mut(read_pos..read_pos + chunk_size) {
                    let read = consumer.pop_slice(chunk);
                    if read == 0 {
                        // Fill remaining buffer with silence
                        chunk.fill(0.0);
                        warn!("Output buffer empty");
                        break;
                    }

                    // Apply EQ processing here
                    if let Ok(bands) = bands.lock() {
                        for sample in chunk.iter_mut() {
                            let gain = bands.iter()
                                .map(|&x| 10.0f32.powf(x / 20.0))
                                .sum::<f32>() / 10.0;
                            *sample = sample.clamp(-1.0, 1.0) * gain;
                        }
                    }
                    read_pos += read;
                } else {
                    error!("Invalid chunk indices: {} to {}", read_pos, read_pos + chunk_size);
                    break;
                }
            }
        };

        device.build_output_stream(
            &config.into(),
            output_data_fn,
            |err| error!("Error in output stream: {}", err),
            None,
        ).map_err(Into::into)
    }
} 