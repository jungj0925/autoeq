import numpy as np
import pyaudio
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSlider, QPushButton
from scipy.signal import butter, lfilter

class EqualizerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Adaptive Audio Equalizer")
        self.setGeometry(100, 100, 400, 300)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.label = QLabel("Adjust Equalizer Bands")
        self.layout.addWidget(self.label)

        # Create sliders for equalizer bands
        self.sliders = []
        for i in range(10):  # 10-band equalizer
            slider = QSlider()
            slider.setOrientation(1)  # Horizontal
            slider.setRange(-12, 12)  # Gain in dB
            slider.setValue(0)  # Default value
            self.layout.addWidget(slider)
            self.sliders.append(slider)

        # Button to apply equalizer settings
        self.apply_button = QPushButton("Apply Equalizer")
        self.apply_button.clicked.connect(self.apply_equalizer)
        self.layout.addWidget(self.apply_button)

        # Initialize audio stream to capture from the virtual audio device
        self.p = pyaudio.PyAudio()
        self.start_stream()

        self.list_audio_devices()

    def start_stream(self):
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,  # Use 2 for stereo input and output
            rate=44100,  # Common sample rate for audio
            input=True,  # Enable audio input
            output=True,  # Enable audio output
            input_device_index=1,  # Index for CABLE Output
            output_device_index=7,  # Index for Speakers (Realtek Audio)
            frames_per_buffer=1024,  # Adjust buffer size as needed
            stream_callback=self.audio_callback  # Callback function for processing audio
        )

    def audio_callback(self, in_data, frame_count, time_info, status):
        # Convert audio data to numpy array
        audio_data = np.frombuffer(in_data, dtype=np.int16)

        # Process the audio data with the equalizer
        processed_data = self.apply_equalizer_to_audio(audio_data)

        # Convert processed data back to bytes and return
        return (processed_data.tobytes(), pyaudio.paContinue)

    # def apply_equalizer_to_audio(self, audio_data):
    #     # Apply filters based on slider values
    #     gains = [slider.value() for slider in self.sliders]
    #     bands = [60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000]  # Frequency bands in Hz

    #     # Initialize output array
    #     output_data = np.zeros_like(audio_data, dtype=np.float32)

    #     for i, gain in enumerate(gains):
    #         if gain != 0:
    #             # Design a band-pass filter
    #             b, a = butter(2, [bands[i] - 50, bands[i] + 50], btype='band', fs=44100)
    #             filtered_data = lfilter(b, a, audio_data)
    #             output_data += filtered_data * (10 ** (gain / 20)) + 0.01  # Add a small constant to avoid silence

    #     # Clip the output data to prevent overflow
    #     output_data = np.clip(output_data, -32768, 32767)
    #     return output_data.astype(np.int16)

    def apply_equalizer(self):
        # This method is now handled in the audio callback
        pass

    def closeEvent(self, event):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
        event.accept()
    def list_audio_devices(self):
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            print(f"Device {i}: {info['name']}, Input Channels: {info['maxInputChannels']}, Output Channels: {info['maxOutputChannels']}")
        p.terminate()

    def apply_equalizer_to_audio(self, audio_data):
        # Frequency bands for the equalizer
        bands = [60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000]

        # Read slider values (gains in dB)
        gains = [slider.value() for slider in self.sliders]
        print(f"Slider values: {gains}")  # Debug slider values

        # Handle silent input
        if np.max(np.abs(audio_data)) < 100:  # Silence threshold
            print("Silent input detected, bypassing filters.")
            return audio_data.astype(np.int16)

        # Handle passthrough when all gains are zero
        if all(gain == 0 for gain in gains):
            print("All gains are 0, bypassing equalizer.")
            return audio_data.astype(np.int16)

        # Initialize processed audio
        processed_audio = np.zeros_like(audio_data, dtype=np.float32)

        for i, gain in enumerate(gains):
            if gain != 0:  # Only process if gain is non-zero
                try:
                    # Normalize band frequencies
                    low = max(1, bands[i] - 100) / (44100 / 2)
                    high = (bands[i] + 100) / (44100 / 2)

                    # Design a stable band-pass filter
                    b, a = butter(1, [low, high], btype='band')  # 1st-order filter

                    # Apply the filter
                    filtered_data = lfilter(b, a, audio_data)

                    # Apply gain (convert dB to linear scale)
                    filtered_data *= 10 ** (gain / 20)

                    # Accumulate the filtered data
                    processed_audio += filtered_data
                except ValueError as e:
                    print(f"Filter design failed for band {bands[i]} Hz: {e}")

        # Add processed audio to the original input for proper mixing
        mixed_audio = audio_data + processed_audio.astype(np.int16)

        # Normalize mixed audio to prevent overflow
        max_val = np.max(np.abs(mixed_audio))
        if max_val > 32767:
            mixed_audio = (mixed_audio / max_val) * 32767

        # Convert to int16 for audio playback
        return np.clip(mixed_audio, -32768, 32767).astype(np.int16)






