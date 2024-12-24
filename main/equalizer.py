import numpy as np
import pyaudio
import pickle
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSlider, QPushButton, QHBoxLayout, QGridLayout,
    QLineEdit, QComboBox, QMessageBox, QSystemTrayIcon, QMenu, QAction
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from scipy.signal import sosfilt


class EqualizerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Adaptive Audio Equalizer")
        self.setGeometry(100, 100, 700, 500)
        self.equalizer_enabled = True  # Bypass mode flag
        self.presets = self.load_all_presets()  # Load all existing presets

        # Main layout
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Title label
        title_label = QLabel("10-Band Audio Equalizer")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
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
            slider.setPageStep(1)
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

        # Presets section
        self.preset_layout = QHBoxLayout()

        # Preset name input
        self.preset_name_input = QLineEdit()
        self.preset_name_input.setPlaceholderText("Enter preset name")
        self.preset_layout.addWidget(self.preset_name_input)

        # Save preset button
        save_button = QPushButton("Save Preset")
        save_button.clicked.connect(self.save_preset)
        self.preset_layout.addWidget(save_button)

        # Load preset dropdown
        self.preset_dropdown = QComboBox()
        self.update_preset_dropdown()
        self.preset_layout.addWidget(self.preset_dropdown)

        # Load preset button
        load_button = QPushButton("Load Preset")
        load_button.clicked.connect(self.load_preset)
        self.preset_layout.addWidget(load_button)

        # Delete preset button
        delete_button = QPushButton("Delete Preset")
        delete_button.clicked.connect(self.delete_preset)
        self.preset_layout.addWidget(delete_button)

        self.main_layout.addLayout(self.preset_layout)

        # Buttons layout
        buttons_layout = QHBoxLayout()

        # Reset button
        reset_button = QPushButton("Reset to 0 dB")
        reset_button.clicked.connect(self.reset_sliders)
        buttons_layout.addWidget(reset_button)

        # Bypass button
        bypass_button = QPushButton("Bypass")
        bypass_button.clicked.connect(self.toggle_bypass)
        buttons_layout.addWidget(bypass_button)

        self.main_layout.addLayout(buttons_layout)

        # System tray integration
        self.tray_icon = QSystemTrayIcon(QIcon("icon.png"), self)
        self.tray_icon.setToolTip("Adaptive Audio Equalizer")
        tray_menu = QMenu()

        toggle_action = QAction("Toggle Equalizer", self)
        toggle_action.triggered.connect(self.toggle_bypass)
        tray_menu.addAction(toggle_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        # Initialize PyAudio
        self.p = pyaudio.PyAudio()

        print("Available Audio Devices:")
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            print(f"Index {i}: {device_info['name']}")

        self.start_stream()

    def reset_sliders(self):
        """Reset all sliders to 0 dB."""
        for slider in self.sliders:
            slider.setValue(0)

    def update_slider_label(self):
        """Update the labels showing current slider values."""
        for i, slider in enumerate(self.sliders):
            self.slider_labels[i].setText(f"{slider.value()} dB")

    def save_preset(self):
        """Save current slider settings with a name."""
        preset_name = self.preset_name_input.text().strip()
        if not preset_name:
            QMessageBox.warning(self, "Error", "Preset name cannot be empty.")
            return
        preset = [slider.value() for slider in self.sliders]
        self.presets[preset_name] = preset
        self.save_all_presets()
        self.update_preset_dropdown()
        QMessageBox.information(self, "Success", f"Preset '{preset_name}' saved!")

    def load_preset(self):
        """Load a preset by name."""
        preset_name = self.preset_dropdown.currentText()
        if not preset_name:
            QMessageBox.warning(self, "Error", "No preset selected.")
            return
        preset = self.presets.get(preset_name)
        if preset is not None:
            for slider, value in zip(self.sliders, preset):
                slider.setValue(value)
            QMessageBox.information(self, "Success", f"Preset '{preset_name}' loaded!")

    def delete_preset(self):
        """Delete the selected preset."""
        preset_name = self.preset_dropdown.currentText()
        if not preset_name:
            QMessageBox.warning(self, "Error", "No preset selected.")
            return
        if preset_name in self.presets:
            del self.presets[preset_name]
            self.save_all_presets()
            self.update_preset_dropdown()
            QMessageBox.information(self, "Success", f"Preset '{preset_name}' deleted!")

    def update_preset_dropdown(self):
        """Update the dropdown menu with available presets."""
        self.preset_dropdown.clear()
        self.preset_dropdown.addItems(self.presets.keys())

    def save_all_presets(self):
        """Save all presets to file."""
        with open("presets.pkl", "wb") as file:
            pickle.dump(self.presets, file)

    def load_all_presets(self):
        """Load all presets from file."""
        try:
            with open("presets.pkl", "rb") as file:
                return pickle.load(file)
        except FileNotFoundError:
            return {}

    def toggle_bypass(self):
        """Toggle the equalizer bypass mode."""
        self.equalizer_enabled = not self.equalizer_enabled
        QMessageBox.information(
            self, "Equalizer Status",
            "Equalizer Enabled" if self.equalizer_enabled else "Equalizer Bypassed"
        )

    def audio_callback(self, in_data, frame_count, time_info, status):
        """Process audio data in real-time."""
        # Convert audio data to numpy array and reshape for stereo
        audio_data = np.frombuffer(in_data, dtype=np.int16).reshape(-1, 2)  # Stereo

        # Check if all gains are zero or if bypass mode is enabled
        if not self.equalizer_enabled or all(slider.value() == 0 for slider in self.sliders):
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
    
    def start_stream(self):
        """Initialize audio stream with dynamic output device detection."""
        p = pyaudio.PyAudio()

        # Fixed input device index
        input_device_index = 1

        # Automatically detect output device
        output_device_index = None
        output_keywords = ["Headphones", "Speakers"]  # Add keywords for preferred devices

        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            device_name = device_info['name']
            for keyword in output_keywords:
                if keyword.lower() in device_name.lower():
                    output_device_index = i
                    print(f"Selected Output Device: Index {i}: {device_name}")
                    break
            if output_device_index is not None:
                break

        if output_device_index is None:
            raise ValueError("No suitable output device found.")

        # Open the audio stream
        self.stream = p.open(
            format=pyaudio.paInt16,
            channels=2,  # Stereo audio
            rate=44100,  # Common sample rate for audio
            input=True,
            output=True,
            input_device_index=input_device_index,  # Fixed input device
            output_device_index=output_device_index,  # Detected output device
            frames_per_buffer=1024,
            stream_callback=self.audio_callback
        )

    def peaking_eq(self, f0, Q, gain_db, sample_rate):
        """
        Design a peaking equalizer biquad filter and return as second-order sections (SOS).
        """
        # Convert gain from dB to linear amplitude
        A = 10 ** (gain_db / 40)
        # Calculate normalized frequency
        omega = 2 * np.pi * f0 / sample_rate
        # Bandwidth control
        alpha = np.sin(omega) / (2 * Q)

        # Filter coefficients
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
        Spotify-style equalizer using peaking EQ filters in SOS format.
        """
        # Sanitize and validate input
        audio_data = np.nan_to_num(audio_data, nan=0.0, posinf=0.0, neginf=0.0)  # Replace NaN/Inf with 0
        if len(audio_data) == 0 or np.max(np.abs(audio_data)) == 0:
            return np.zeros_like(audio_data).astype(np.int16)

        # Calculate RMS and handle silence
        rms = np.sqrt(np.mean(audio_data**2))
        if rms < 0.01:  # Treat near-silent signals as silence
            return audio_data.astype(np.int16)

        # Initialize parameters
        bands = self.bands  # Center frequencies for bands
        gains = [slider.value() for slider in self.sliders]  # Gains in dB
        sample_rate = 44100
        processed_audio = audio_data.astype(np.float32)

        for i, gain in enumerate(gains):
            if gain == 0:  # Skip bands with no adjustment
                continue

            # Clamp extreme gain values to avoid instability
            gain = max(min(gain, 6), -6)  # Limit to ±6 dB for stability

            try:
                # Use peaking EQ filter
                f0 = bands[i]
                Q = 1.0  # Adjust Q for smoother filtering
                sos = self.peaking_eq(f0, Q, gain, sample_rate)  # Get SOS array
                band_audio = sosfilt(sos, processed_audio)

                # Blend filtered band into processed audio
                processed_audio += band_audio * (10 ** (gain / 20))  # Apply gain in linear scale
            except ValueError as e:
                print(f"Filter design failed for band {bands[i]} Hz: {e}")

        # Normalize processed audio
        max_val = np.max(np.abs(processed_audio))
        if max_val > 0:  # Prevent division by zero
            processed_audio = (processed_audio / max_val) * 32767

        # Apply a final low-pass filter to reduce high-frequency noise
        try:
            sos_lowpass = self.peaking_eq(20000, 0.7, 0, sample_rate)  # Smoothen output
            processed_audio = sosfilt(sos_lowpass, processed_audio)
        except ValueError as e:
            print(f"Low-pass filter design failed: {e}")

        # Clip and return as int16
        return np.clip(processed_audio, -32768, 32767).astype(np.int16)