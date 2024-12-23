import numpy as np
import pyaudio
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSlider, QPushButton, QHBoxLayout, QGridLayout
from PyQt5.QtCore import Qt
from scipy.signal import butter, lfilter
from scipy.signal import sosfilt, iirfilter



class EqualizerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Adaptive Audio Equalizer")
        self.setGeometry(100, 100, 600, 400)

        # Main layout
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Title label
        title_label = QLabel("10-Band Audio Equalizer")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.main_layout.addWidget(title_label)

        # Sliders layout
        self.sliders_layout = QGridLayout()
        self.sliders = []
        self.slider_labels = []

        # Frequency bands
        self.bands = [60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000]

        for i, band in enumerate(self.bands):
            # Band label
            band_label = QLabel(f"{band} Hz")
            band_label.setAlignment(Qt.AlignCenter)
            self.sliders_layout.addWidget(band_label, 0, i)

            # Slider
            slider = QSlider(Qt.Vertical)
            slider.setRange(-12, 12)  # Gain range in dB
            slider.setValue(0)  # Default value
            slider.setToolTip(f"Adjust {band} Hz gain")
            slider.valueChanged.connect(self.update_slider_label)
            self.sliders.append(slider)
            self.sliders_layout.addWidget(slider, 1, i)

            # Current gain label
            slider_label = QLabel("0 dB")
            slider_label.setAlignment(Qt.AlignCenter)
            self.slider_labels.append(slider_label)
            self.sliders_layout.addWidget(slider_label, 2, i)

        self.main_layout.addLayout(self.sliders_layout)

        # Buttons layout
        buttons_layout = QHBoxLayout()

        # Reset button
        reset_button = QPushButton("Reset to 0 dB")
        reset_button.setToolTip("Reset all sliders to 0 dB")
        reset_button.clicked.connect(self.reset_sliders)
        buttons_layout.addWidget(reset_button)

        # Apply button
        apply_button = QPushButton("Apply Equalizer")
        apply_button.setToolTip("Apply equalizer settings")
        apply_button.clicked.connect(self.apply_equalizer)
        buttons_layout.addWidget(apply_button)

        self.main_layout.addLayout(buttons_layout)

        # Initialize PyAudio
        self.p = pyaudio.PyAudio()
        self.start_stream()

    def reset_sliders(self):
        """Reset all sliders to 0 dB."""
        for slider in self.sliders:
            slider.setValue(0)

    def update_slider_label(self):
        """Update the labels showing current slider values."""
        for i, slider in enumerate(self.sliders):
            self.slider_labels[i].setText(f"{slider.value()} dB")

    def apply_equalizer(self):
        """Apply the current equalizer settings."""
        print("Equalizer settings applied:")
        for i, slider in enumerate(self.sliders):
            print(f"{self.bands[i]} Hz: {slider.value()} dB")

    def closeEvent(self, event):
        """Handle window close event."""
        if hasattr(self, 'stream') and self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
        event.accept()

    def start_stream(self):
        """Initialize audio stream."""
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=2,  # Stereo audio
            rate=44100,  # Common sample rate for audio
            input=True,
            output=True,
            input_device_index=1,  # Index for CABLE Output
            output_device_index=7,  # Index for Speakers (Realtek Audio)
            frames_per_buffer=1024,
            stream_callback=self.audio_callback
        )

    def audio_callback(self, in_data, frame_count, time_info, status):
        """Process audio data in real-time."""
        # Convert audio data to numpy array and reshape for stereo
        audio_data = np.frombuffer(in_data, dtype=np.int16).reshape(-1, 2)  # Stereo

        # Check if all gains are zero
        if all(slider.value() == 0 for slider in self.sliders):
            # Pass through original audio when no adjustments
            return (in_data, pyaudio.paContinue)

        # Split into left and right channels
        left_channel = audio_data[:, 0]
        right_channel = audio_data[:, 1]

        # Process each channel independently
        processed_left = self.apply_equalizer_to_audio(left_channel)
        processed_right = self.apply_equalizer_to_audio(right_channel)

        # Combine back into stereo
        processed_data = np.column_stack((processed_left, processed_right)).flatten()

        # Convert processed data back to bytes and return
        return (processed_data.tobytes(), pyaudio.paContinue)

    def peaking_eq(self, f0, Q, gain_db, sample_rate):
        """
        Design a peaking equalizer biquad filter and return as second-order sections (SOS).
        """
        A = 10 ** (gain_db / 40)  # Convert dB to linear amplitude
        omega = 2 * np.pi * f0 / sample_rate
        alpha = np.sin(omega) / (2 * Q)

        b0 = 1 + alpha * A
        b1 = -2 * np.cos(omega)
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * np.cos(omega)
        a2 = 1 - alpha / A

        # Normalize coefficients
        b = [b0 / a0, b1 / a0, b2 / a0]
        a = [1.0, a1 / a0, a2 / a0]

        # Combine into second-order sections (SOS) format
        sos = np.hstack([b, a])
        return np.array([sos])

    def apply_equalizer_to_audio(self, audio_data):
        """
        Refined equalizer: Handle gains properly and reduce distortions.
        """
        # Sanitize and validate input
        audio_data = np.nan_to_num(audio_data, nan=0.0, posinf=0.0, neginf=0.0)
        if len(audio_data) == 0 or np.max(np.abs(audio_data)) == 0:
            return np.zeros_like(audio_data).astype(np.int16)

        # High-pass filter to remove subsonic frequencies
        sos_hp = butter(1, 20 / (44100 / 2), btype='highpass', output='sos')  # High-pass filter in SOS format
        audio_data = sosfilt(sos_hp, audio_data)

        # Calculate RMS and handle silence
        rms = np.sqrt(np.mean(audio_data**2))
        if rms < 0.01:
            return audio_data.astype(np.int16)

        # Initialize parameters
        bands = self.bands  # Center frequencies for bands
        gains = [slider.value() for slider in self.sliders]  # Gains in dB
        sample_rate = 44100
        processed_audio = np.zeros_like(audio_data, dtype=np.float32)

        for i, gain in enumerate(gains):
            if gain == 0:  # Skip bands with no adjustment
                continue

            try:
                # Use peaking EQ filter
                f0 = bands[i]
                Q = 0.7 if f0 < 250 else 2.0  # Broader filter for low frequencies
                sos = self.peaking_eq(f0, Q, gain, sample_rate)  # Get SOS array

                # Apply the filter to the original audio
                band_audio = sosfilt(sos, audio_data)

                # Scale the band contribution by the gain factor
                gain_factor = 10 ** (gain / 20) if gain > 0 else 10 ** (gain / 20)
                band_audio *= gain_factor

                # Mix filtered band into processed audio
                processed_audio += band_audio
            except ValueError as e:
                print(f"Filter design failed for band {bands[i]} Hz: {e}")

        # Blend processed and original audio for smoother output
        mixed_audio = 0.7 * audio_data + 0.3 * processed_audio

        # Normalize processed audio
        max_val = np.max(np.abs(mixed_audio))
        if max_val > 32767:
            mixed_audio = (mixed_audio / max_val) * 32767

        # Clip and return as int16
        return np.clip(mixed_audio, -32768, 32767).astype(np.int16)

