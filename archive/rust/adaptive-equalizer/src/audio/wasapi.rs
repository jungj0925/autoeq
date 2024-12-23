// src/audio/wasapi.rs
use anyhow::Result;
use std::ptr;
use windows::Win32::Media::Audio::{
    IAudioClient, IAudioCaptureClient, IMMDevice, IMMDeviceEnumerator,
    MMDeviceEnumerator, eRender, eMultimedia,
    AUDCLNT_SHAREMODE_SHARED, AUDCLNT_STREAMFLAGS_LOOPBACK,
    WAVEFORMATEX,
};
use windows::Win32::System::Com::{
    CoCreateInstance, CoInitializeEx, CoUninitialize,
    CLSCTX_ALL, COINIT_APARTMENTTHREADED,
};
use log::{error, info};

#[derive(Clone)]
pub struct WasapiCapture {
    client: Option<IAudioClient>,
    capture_client: Option<IAudioCaptureClient>,
    format: Option<WAVEFORMATEX>,
}

impl WasapiCapture {
    pub fn new() -> Result<Self> {
        unsafe {
            CoInitializeEx(ptr::null_mut(), COINIT_APARTMENTTHREADED)?;

            let device_enumerator: IMMDeviceEnumerator = MMDeviceEnumerator::new()?;
            let device: IMMDevice = device_enumerator.GetDefaultAudioEndpoint(eRender, eMultimedia)?;

            let client: IAudioClient = device.Activate(&IAudioClient::uuidof(), CLSCTX_ALL, ptr::null_mut())?;
            let mut mix_format: *mut WAVEFORMATEX = ptr::null_mut();
            client.GetMixFormat(&mut mix_format)?;

            let format = *mix_format;

            client.Initialize(
                AUDCLNT_SHAREMODE_SHARED,
                AUDCLNT_STREAMFLAGS_LOOPBACK,
                0,
                0,
                &format,
                ptr::null_mut(),
            )?;

            let capture_client: IAudioCaptureClient = client.GetService()?;

            Ok(WasapiCapture {
                client: Some(client),
                capture_client: Some(capture_client),
                format: Some(format),
            })
        }
    }

    pub fn capture_data(&mut self) -> Result<Vec<f32>> {
        unsafe {
            if let Some(capture_client) = &self.capture_client {
                let mut next_packet_size = 0;
                capture_client.GetNextPacketSize(&mut next_packet_size)?;

                if next_packet_size > 0 {
                    let mut buffer_data: *mut std::ffi::c_void = ptr::null_mut();
                    let mut num_frames_to_read = 0;
                    let mut flags = 0;

                    capture_client.GetBuffer(
                        &mut buffer_data,
                        &mut num_frames_to_read,
                        &mut flags,
                        None,
                        None,
                    )?;

                    let slice = std::slice::from_raw_parts(buffer_data as *const f32, num_frames_to_read as usize);
                    let output_data = slice.to_vec();

                    capture_client.ReleaseBuffer(num_frames_to_read)?;
                    return Ok(output_data);
                }
            }
            Ok(vec![])
        }
    }
}

impl Drop for WasapiCapture {
    fn drop(&mut self) {
        unsafe {
            if let Some(client) = &self.client {
                client.Stop().ok();
            }
            CoUninitialize();
        }
    }
}