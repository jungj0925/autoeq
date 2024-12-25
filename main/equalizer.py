import numpy as np
import pyaudio
import pickle
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSlider, QPushButton, QHBoxLayout, QGridLayout,
    QLineEdit, QComboBox, QMessageBox, QSystemTrayIcon, QMenu, QAction
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QFont
from scipy.signal import sosfilt
from spotify_integration import SpotifyIntegration

class EqualizerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Adaptive Audio Equalizer")
        self.setGeometry(100, 100, 700, 600)
        self.equalizer_enabled = True  # Bypass mode flag

        # Presets (Genres and Custom)
        self.genre_presets = self.get_genre_presets()
        self.custom_presets = self.load_custom_presets()

        # Spotify Integration
        self.spotify = SpotifyIntegration()

        # Main layout
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Title label
        title_label = QLabel("Adaptive Audio Equalizer")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.main_layout.addWidget(title_label)

        # Spotify "Now Playing" section
        self.now_playing_label = QLabel("Currently streaming: Not Available")
        self.now_playing_label.setAlignment(Qt.AlignCenter)
        self.now_playing_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.now_playing_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        self.main_layout.addWidget(self.now_playing_label)

        # Spotify Login Button
        self.spotify_login_button = QPushButton("Log in to Spotify")
        self.spotify_login_button.clicked.connect(self.spotify_log_in)
        self.main_layout.addWidget(self.spotify_login_button)

        # Timer to update the "Now Playing" label
        self.song_update_timer = QTimer(self)
        self.song_update_timer.timeout.connect(self.update_now_playing)
        self.song_update_timer.start(1000)  # Update every 1 second

        # Equalizer sliders layout
        self.sliders_layout = QGridLayout()
        self.sliders = []
        self.slider_labels = []

        # Frequency bands
        self.bands = [60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000]

        for i, band in enumerate(self.bands):
            band_label = QLabel(f"{band} Hz")
            band_label.setAlignment(Qt.AlignCenter)
            self.sliders_layout.addWidget(band_label, 0, i)

            slider = QSlider(Qt.Vertical)
            slider.setRange(-12, 12)  # Gain range in dB
            slider.setValue(0)  # Default value for Flat EQ
            slider.setPageStep(1)
            slider.setToolTip(f"Adjust {band} Hz gain")
            slider.valueChanged.connect(self.update_slider_label)
            self.sliders.append(slider)
            self.sliders_layout.addWidget(slider, 1, i)

            slider_label = QLabel("0 dB")
            slider_label.setAlignment(Qt.AlignCenter)
            self.slider_labels.append(slider_label)
            self.sliders_layout.addWidget(slider_label, 2, i)

        self.main_layout.addLayout(self.sliders_layout)

        # Presets section
        self.preset_layout = QHBoxLayout()

        # Preset dropdown
        self.preset_dropdown = QComboBox()
        self.update_preset_dropdown()
        self.preset_dropdown.setCurrentText("Flat")  # Default to Flat
        self.preset_dropdown.currentTextChanged.connect(self.apply_preset)
        self.preset_layout.addWidget(self.preset_dropdown)

        # Save custom preset button
        self.preset_name_input = QLineEdit()
        self.preset_name_input.setPlaceholderText("Enter custom preset name")
        self.preset_layout.addWidget(self.preset_name_input)

        save_custom_button = QPushButton("Save Custom")
        save_custom_button.clicked.connect(self.save_custom_preset)
        self.preset_layout.addWidget(save_custom_button)

        # Delete custom preset button
        delete_custom_button = QPushButton("Delete Custom")
        delete_custom_button.clicked.connect(self.delete_custom_preset)
        self.preset_layout.addWidget(delete_custom_button)

        self.main_layout.addLayout(self.preset_layout)

        # Buttons layout
        buttons_layout = QHBoxLayout()

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

        self.auto_eq_enabled = True  # Default to Auto EQ enabled

        # Auto EQ toggle button
        auto_eq_button = QPushButton("Toggle Auto EQ")
        auto_eq_button.setToolTip("Enable or disable automatic genre-based equalizer adjustment")
        auto_eq_button.clicked.connect(self.toggle_auto_eq)
        buttons_layout.addWidget(auto_eq_button)

        # Initialize PyAudio
        self.p = pyaudio.PyAudio()

        print("Available Audio Devices:")
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            print(f"Index {i}: {device_info['name']}")

        self.start_stream()

    def spotify_log_in(self):
        """Handle Spotify login process."""
        if self.spotify.log_in():
            QMessageBox.information(self, "Spotify Login", "Logged in successfully!")
        else:
            QMessageBox.critical(self, "Spotify Login", "Login failed. Please try again.")

    def update_preset_dropdown(self):
        """Update the dropdown menu with genre and custom presets."""
        self.preset_dropdown.clear()
        self.preset_dropdown.addItem("Flat")  # Default Flat EQ
        self.preset_dropdown.addItems(list(self.genre_presets.keys()) + list(self.custom_presets.keys()))

    def apply_preset(self):
        """Apply the selected preset to the sliders."""
        preset_name = self.preset_dropdown.currentText()
        if preset_name == "Flat":
            values = [0] * len(self.bands)  # Flat preset
        elif preset_name in self.genre_presets:
            values = self.genre_presets[preset_name]
        elif preset_name in self.custom_presets:
            values = self.custom_presets[preset_name]
        else:
            return  # No valid preset selected

        for slider, value in zip(self.sliders, values):
            slider.setValue(value)

    def reset_sliders(self):
        """Reset all sliders to 0 dB."""
        for slider in self.sliders:
            slider.setValue(0)

    def get_genre_presets(self):
        """Return a dictionary of pre-defined genre presets."""
        return {
            "Pop": [2, 1, 0, 0, 2, 3, 2, 3, 2, 1],
            "Rock": [4, 3, 2, 1, 0, 1, 0, -1, -2, -2],
            "Classical": [0, 0, 1, 1, 2, 3, 2, 3, 2, 1],
            "Jazz": [2, 3, 2, 1, 1, 2, 1, 1, 1, 0],
            "Hip-Hop": [6, 4, 2, 1, 0, 2, 3, 4, 2, 1],
            "Electronic": [6, 4, 3, 2, 0, 2, 4, 6, 5, 3],
            "Acoustic": [1, 1, 2, 2, 3, 3, 2, 2, 1, 0],
            "Metal": [5, 4, 3, 1, 1, 1, 0, -1, -2, -3],
            "Dance": [5, 3, 2, 1, 0, 2, 4, 5, 3, 2],
            "R&B": [4, 3, 2, 1, 1, 1, 2, 2, 1, 0]
        }

    def update_now_playing(self):
        """Fetch and update the 'Now Playing' label with genre detection."""
        if not self.auto_eq_enabled:
            return

        song_info = self.spotify.get_current_song()
        if song_info:
            sub_genres = self.spotify.get_genres_for_song()
            if sub_genres:
                broad_genre = self.spotify.predict_broad_genre(sub_genres)
                self.now_playing_label.setText(f"Currently streaming: {song_info} ({broad_genre})")
                
                # Automatically apply the equalizer preset for the detected genre
                self.apply_preset_by_name(broad_genre)
            else:
                self.now_playing_label.setText(f"Currently streaming: {song_info} (Genre: Unknown)")
        else:
            self.now_playing_label.setText("Currently streaming: Not Available")

    def toggle_auto_eq(self):
        """Toggle the Auto EQ feature."""
        self.auto_eq_enabled = not self.auto_eq_enabled
        status = "enabled" if self.auto_eq_enabled else "disabled"
        QMessageBox.information(self, "Auto EQ Status", f"Auto EQ is now {status}.")


    def save_custom_preset(self):
        """Save current slider settings as a custom preset."""
        preset_name = self.preset_name_input.text().strip()
        if not preset_name:
            QMessageBox.warning(self, "Error", "Preset name cannot be empty.")
            return

        # Prevent overwriting genre presets
        if preset_name in self.genre_presets:
            QMessageBox.warning(self, "Error", "Preset name conflicts with a genre preset.")
            return

        values = [slider.value() for slider in self.sliders]
        self.custom_presets[preset_name] = values
        self.save_custom_presets()
        self.update_preset_dropdown()
        QMessageBox.information(self, "Success", f"Custom preset '{preset_name}' saved!")

    def save_custom_presets(self):
        """Save custom presets to a file."""
        with open("custom_presets.pkl", "wb") as file:
            pickle.dump(self.custom_presets, file)

    def load_custom_presets(self):
        """Load custom presets from a file."""
        try:
            with open("custom_presets.pkl", "rb") as file:
                return pickle.load(file)
        except (FileNotFoundError, EOFError, pickle.UnpicklingError):
            return {}

    def delete_custom_preset(self):
        """Delete the selected custom preset."""
        preset_name = self.preset_dropdown.currentText()
        if not preset_name or preset_name in self.genre_presets:
            QMessageBox.warning(self, "Error", "Cannot delete a genre preset or an invalid preset.")
            return
        if preset_name in self.custom_presets:
            del self.custom_presets[preset_name]
            self.save_custom_presets()
            self.update_preset_dropdown()
            QMessageBox.information(self, "Success", f"Custom preset '{preset_name}' deleted!")

    def update_slider_label(self):
        """Update the labels showing current slider values."""
        for i, slider in enumerate(self.sliders):
            self.slider_labels[i].setText(f"{slider.value()} dB")

    def toggle_bypass(self):
        """Toggle the equalizer bypass mode."""
        self.equalizer_enabled = not self.equalizer_enabled
        QMessageBox.information(
            self, "Equalizer Status",
            "Equalizer Enabled" if self.equalizer_enabled else "Equalizer Bypassed"
        )

    def apply_preset_by_name(self, preset_name):
        """
        Apply a preset by its name and update the dropdown menu.
        """
        if preset_name in self.genre_presets:
            values = self.genre_presets[preset_name]
            for slider, value in zip(self.sliders, values):
                slider.setValue(value)
            # Update the dropdown to match the applied preset
            self.preset_dropdown.blockSignals(True)  # Prevent triggering signal
            self.preset_dropdown.setCurrentText(preset_name)
            self.preset_dropdown.blockSignals(False)
        else:
            QMessageBox.warning(self, "Error", f"No preset found for genre: {preset_name}")


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
        input_device_index = 1  # Ensure this is correct for your setup

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
        Spotify-style equalizer using peaking EQ filters in SOS format, with gain compensation.
        """
        # Sanitize and validate input
        audio_data = np.nan_to_num(audio_data, nan=0.0, posinf=0.0, neginf=0.0)
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
        processed_audio = np.zeros_like(audio_data, dtype=np.float32)

        # Accumulate energy normalization factor
        total_gain = 0.0
        gain_factors = []

        for i, gain in enumerate(gains):
            if gain == 0:  # Skip bands with no adjustment
                continue

            try:
                # Use peaking EQ filter
                f0 = bands[i]
                Q = 1.0  # Standard Q for smooth filtering
                sos = self.peaking_eq(f0, Q, gain, sample_rate)  # Get SOS array

                # Apply the filter
                band_audio = sosfilt(sos, audio_data)

                # Convert gain from dB to linear scale and track total gain
                gain_factor = 10 ** (gain / 20)
                processed_audio += band_audio * gain_factor
                gain_factors.append(gain_factor)
                total_gain += gain_factor
            except ValueError as e:
                print(f"Filter design failed for band {bands[i]} Hz: {e}")

        # Normalize by the total applied gain to prevent overall volume increase
        if total_gain > 0:
            processed_audio /= total_gain

        # Normalize processed audio to prevent clipping
        max_val = np.max(np.abs(processed_audio))
        if max_val > 32767:
            processed_audio = (processed_audio / max_val) * 32767

        # Clip the final output to the int16 range
        return np.clip(processed_audio, -32768, 32767).astype(np.int16)
