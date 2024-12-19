import numpy as np
from scipy.signal import butter, sosfilt
import sounddevice as sd
import threading
import time

class Equalizer:
    def __init__(self):
        self.running = False
        self.frequency_bands = [60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000]
        self.eq_values = [0.0] * len(self.frequency_bands)
        self.sample_rate = 44100
        self.chunk_size = 1024
        self.channels = 2
        
        # Create bandpass filters for each frequency band
        self.filters = []
        for i, freq in enumerate(self.frequency_bands):
            if i == 0:  # Lowest band - lowpass
                sos = butter(8, freq * 1.5, btype='lowpass', fs=self.sample_rate, output='sos')
            elif i == len(self.frequency_bands) - 1:  # Highest band - highpass
                sos = butter(8, freq * 0.7, btype='highpass', fs=self.sample_rate, output='sos')
            else:  # Mid bands - bandpass with overlapping
                bandwidth = (self.frequency_bands[i+1] / freq) ** 0.5
                sos = butter(8, [freq / bandwidth, freq * bandwidth], 
                           btype='band', fs=self.sample_rate, output='sos')
            self.filters.append(sos)
        
        # Initialize device indices
        self.input_device = None
        self.output_device = None
        self.stream = None
        self.list_devices()

    def list_devices(self):
        """List all available audio devices with detailed information"""
        print("\nAvailable audio devices:")
        print("Input Devices:")
        print("--------------")
        for i, device in enumerate(sd.query_devices()):
            if device['max_input_channels'] > 0:
                print(f"[{i}] {device['name']}")
                print(f"    Channels: {device['max_input_channels']}")
                print(f"    Sample Rate: {device['default_samplerate']}")
                if 'Stereo Mix' in device['name'] or 'What U Hear' in device['name']:
                    print("    (Recommended for system audio capture)")
        
        print("\nOutput Devices:")
        print("--------------")
        for i, device in enumerate(sd.query_devices()):
            if device['max_output_channels'] > 0:
                print(f"[{i}] {device['name']}")
                print(f"    Channels: {device['max_output_channels']}")
                print(f"    Sample Rate: {device['default_samplerate']}")

    def set_devices(self, input_device=None, output_device=None):
        """Set input and output devices by their indices"""
        if input_device is not None:
            try:
                device_info = sd.query_devices(input_device)
                if device_info['max_input_channels'] > 0:
                    self.input_device = input_device
                    print(f"Input device set to: {device_info['name']}")
                else:
                    print("Selected device doesn't support input!")
            except:
                print("Invalid input device index!")
        
        if output_device is not None:
            try:
                device_info = sd.query_devices(output_device)
                if device_info['max_output_channels'] > 0:
                    self.output_device = output_device
                    print(f"Output device set to: {device_info['name']}")
                else:
                    print("Selected device doesn't support output!")
            except:
                print("Invalid output device index!")

        # Restart stream if it's running
        if self.running:
            self.stop_auto_eq()
            self.start_auto_eq()

    def process_audio(self, indata, outdata, frames, time, status):
        """Real-time audio processing callback"""
        if status:
            print(status)
        try:
            # Process each channel
            for ch in range(self.channels):
                # Start with input audio
                output = np.zeros_like(indata[:, ch])
                
                # Apply each filter band
                for filter_sos, gain in zip(self.filters, self.eq_values):
                    # Apply filter and gain
                    filtered = sosfilt(filter_sos, indata[:, ch])
                    output += filtered * (10 ** (gain / 20))
                
                # Assign to output buffer
                outdata[:, ch] = output
            
            # Prevent clipping
            max_val = np.max(np.abs(outdata))
            if max_val > 1.0:
                outdata /= max_val
                
        except Exception as e:
            print(f"Processing error: {e}")
            outdata[:] = indata  # Pass through original audio on error

    def start_auto_eq(self):
        """Start audio processing"""
        if self.running:
            return
            
        try:
            # Use WASAPI for better performance
            wasapi_settings = {
                'channels': self.channels,
                'dtype': np.float32,
                'samplerate': self.sample_rate,
                'blocksize': self.chunk_size,
                'callback': self.process_audio,
                'latency': 'low',
                'device': (self.input_device, self.output_device) if self.input_device is not None else None,
                'api': 'Windows WASAPI'
            }
            
            self.stream = sd.Stream(**wasapi_settings)
            self.stream.start()
            self.running = True
            print("Audio processing started")
            
        except Exception as e:
            print(f"Error starting audio stream: {e}")
            self.running = False

    def stop_auto_eq(self):
        """Stop audio processing"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.running = False
        print("Audio processing stopped")

    def set_manual_eq(self, eq_values):
        """Update EQ values"""
        self.eq_values = eq_values
        print(f"EQ values updated: {list(zip(self.frequency_bands, eq_values))}")

    def play_test_sweep(self, duration=3):
        """Play a test sweep through all frequency bands"""
        if not self.running:
            print("Start the EQ first to play test sweep")
            return
            
        try:
            # Generate sweep
            t = np.linspace(0, duration, int(self.sample_rate * duration))
            frequencies = np.logspace(np.log10(20), np.log10(20000), len(t))
            sweep = 0.5 * np.sin(2 * np.pi * frequencies * t)
            
            # Play through current stream
            sd.play(sweep, self.sample_rate)
            sd.wait()
            print("Test sweep complete")
            
        except Exception as e:
            print(f"Error playing test sweep: {e}")
