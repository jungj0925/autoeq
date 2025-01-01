import numpy as np
import pyaudio
import pickle
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSlider, QPushButton, QHBoxLayout, QGridLayout,
    QLineEdit, QComboBox, QMessageBox, QSystemTrayIcon, QMenu, QAction
)
import os
import sys
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from scipy.signal import sosfilt
from spotify_integration import SpotifyIntegration

STYLE_SHEET = """
QPushButton {
    background-color: #3498db;  /* Blue background */
    color: white;
    border: none;
    border-radius: 5px;
    padding: 5px 20px;  /* More padding for a better touch target */
    font-size: 12px;
}

QPushButton:hover {
    background-color: #2980b9;  /* Darker blue on hover */
}
"""

def get_resource_path(relative_path):
    """
    Get the absolute path to a resource, works for PyInstaller bundled environments.
    """
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller extracts resources to a temporary folder
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class EqualizerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoEQ")
        self.setGeometry(100, 100, 900, 700)
        self.equalizer_enabled = True
        self.auto_eq_enabled = True
        self.artist_genres = self.load_artist_genres()

        # Initialize presets
        self.default_genre_presets = self.get_default_genre_presets()
        self.genre_presets = self.get_genre_presets()
        self.custom_presets = self.load_custom_presets()

        # Initialize Spotify Integration
        self.spotify = SpotifyIntegration()

        self.init_ui()
        self.init_audio()

    def init_ui(self):
        """Set up the user interface components."""
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Load and apply styles from QSS file
        
        self.setStyleSheet(STYLE_SHEET)

        # Title label
        self.add_title_label("AutoEQ")

        # Spotify "Now Playing" Section
        self.add_now_playing_section()

        # Equalizer Sliders
        self.add_sliders()

        # Preset Controls
        self.add_preset_controls()

        # Additional Controls
        self.add_buttons()

        # System Tray Integration
        self.setup_tray_icon()

        # Artist Genre Controls
        self.add_artist_genre_controls()


    def add_title_label(self, title):
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(title_label)

    def add_now_playing_section(self):
        self.now_playing_label = QLabel("Currently streaming: Not Available")
        self.now_playing_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.now_playing_label)

        self.song_update_timer = QTimer(self)
        self.song_update_timer.timeout.connect(self.update_now_playing)
        self.song_update_timer.start(1000)

    def add_sliders(self):
        self.sliders_layout = QGridLayout()
        self.sliders = []
        self.slider_labels = []
        

        self.bands = [60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000]
        for i, band in enumerate(self.bands):
            band_label = QLabel(f"{band} Hz")
            band_label.setAlignment(Qt.AlignCenter)
            self.sliders_layout.addWidget(band_label, 0, i)

            slider = QSlider(Qt.Vertical)
            slider.setRange(-12, 12)
            slider.setValue(0)
            slider.setSingleStep(1)
            slider.setPageStep(1)
            slider.valueChanged.connect(self.update_slider_label)
            self.sliders.append(slider)
            self.sliders_layout.addWidget(slider, 1, i)

            slider_label = QLabel("0 dB")
            slider_label.setAlignment(Qt.AlignCenter)
            self.slider_labels.append(slider_label)
            self.sliders_layout.addWidget(slider_label, 2, i)

        self.main_layout.addLayout(self.sliders_layout)

    def add_preset_controls(self):
        self.preset_layout = QHBoxLayout()

        self.preset_dropdown = QComboBox()
        self.update_preset_dropdown()
        self.preset_dropdown.currentTextChanged.connect(self.apply_preset)
        self.preset_layout.addWidget(self.preset_dropdown)

        self.preset_name_input = QLineEdit()
        self.preset_name_input.setPlaceholderText("Enter custom preset name")
        self.preset_layout.addWidget(self.preset_name_input)

        save_button = QPushButton("Save Custom")
        save_button.clicked.connect(self.save_custom_preset)
        self.preset_layout.addWidget(save_button)

        delete_button = QPushButton("Delete Custom")
        delete_button.clicked.connect(self.delete_custom_preset)
        self.preset_layout.addWidget(delete_button)

        reset_button = QPushButton("Reset Preset")
        reset_button.clicked.connect(self.reset_selected_genre_preset)
        self.preset_layout.addWidget(reset_button)

        self.main_layout.addLayout(self.preset_layout)

    def add_buttons(self):
        buttons_layout = QHBoxLayout()

        self.bypass_button = QPushButton("Equalizer: Enabled" if self.equalizer_enabled else "Equalizer: Bypassed")
        self.bypass_button.clicked.connect(self.toggle_bypass)
        buttons_layout.addWidget(self.bypass_button)

        self.auto_eq_button = QPushButton("Auto EQ: Enabled" if self.auto_eq_enabled else "Auto EQ: Disabled")
        self.auto_eq_button.clicked.connect(self.toggle_auto_eq)
        buttons_layout.addWidget(self.auto_eq_button)

        # Add a button to refresh output device
        refresh_app_button = QPushButton("Refresh App")
        refresh_app_button.clicked.connect(self.confirm_restart)
        buttons_layout.addWidget(refresh_app_button)

        # # Add a button to refresh Spotify login
        # refresh_login_button = QPushButton("Refresh Spotify Login")
        # refresh_login_button.clicked.connect(self.refresh_spotify_login)
        # buttons_layout.addWidget(refresh_login_button)

        self.main_layout.addLayout(buttons_layout)

    def setup_tray_icon(self):
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

    def init_audio(self):
        """Initialize the audio stream."""
        self.p = pyaudio.PyAudio()
        print("Available Audio Devices:")
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            print(f"Index {i}: {device_info['name']}")
        self.start_stream()

    def update_preset_dropdown(self):
        """Update the dropdown menu with genre and custom presets."""
        self.preset_dropdown.clear()
        self.preset_dropdown.addItem("Flat")  # Default Flat EQ
        self.preset_dropdown.addItems(list(self.genre_presets.keys()) + list(self.custom_presets.keys()))

    def add_artist_genre_controls(self):
        layout = QHBoxLayout()

        # Artist input (auto-filled)
        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("Enter artist name")
        self.artist_input.setReadOnly(True)  # Make it read-only for autofill
        layout.addWidget(self.artist_input)

        # Genre input
        self.genre_input = QLineEdit()
        self.genre_input.setPlaceholderText("Enter genre")
        layout.addWidget(self.genre_input)

        # Assign genre button
        self.assign_button = QPushButton("Assign Genre/EQ")
        self.assign_button.clicked.connect(self.assign_genre_to_artist)
        layout.addWidget(self.assign_button)

        # Reset genre button
        self.reset_button = QPushButton("Reset Genre")
        self.reset_button.clicked.connect(self.reset_genre_for_artist)
        layout.addWidget(self.reset_button)

        self.main_layout.addLayout(layout)



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

    def update_now_playing(self):
        """Fetch and update the 'Now Playing' label with genre detection."""
        song_info = self.spotify.get_current_song()
        if song_info:
            artist_name = song_info.split(" by ")[1]

            # Autofill the artist input field
            self.artist_input.setText(artist_name)

            # Check if the artist has an assigned genre
            if artist_name in self.artist_genres:
                assigned_genre = self.artist_genres[artist_name]
                self.now_playing_label.setText(f"Currently streaming: {song_info} ({assigned_genre})")
                if self.auto_eq_enabled:
                    self.apply_preset_by_name(assigned_genre)
            else:
                sub_genres = self.spotify.get_genres_for_song(artist_name)
                if sub_genres:
                    broad_genre = self.spotify.predict_broad_genre(sub_genres)
                    self.now_playing_label.setText(f"Currently streaming: {song_info} ({broad_genre})")
                    if self.auto_eq_enabled:
                        self.apply_preset_by_name(broad_genre)
                else:
                    self.now_playing_label.setText(f"Currently streaming: {song_info} (Genre: Unknown)")
                    self.genre_input.clear()  # Clear the genre field for a new assignment
        else:
            self.now_playing_label.setText("Currently streaming: Not Available")
            self.artist_input.clear()
            self.genre_input.clear()



    def toggle_auto_eq(self):
        """Toggle the Auto EQ feature."""
        self.auto_eq_enabled = not self.auto_eq_enabled
        self.auto_eq_button.setText("Auto EQ: Enabled" if self.auto_eq_enabled else "Auto EQ: Disabled")

    def save_custom_preset(self):
        """
        Save current slider settings as a custom preset or update an existing genre preset.
        """
        preset_name = self.preset_name_input.text().strip()
        if not preset_name:
            QMessageBox.warning(self, "Error", "Preset name cannot be empty.")
            return

        values = [slider.value() for slider in self.sliders]

        # Check if the selected preset is a predefined genre
        if preset_name in self.genre_presets:
            # Ask the user if they want to overwrite the genre preset
            reply = QMessageBox.question(
                self,
                "Overwrite Genre Preset",
                f"The preset '{preset_name}' is a predefined genre. Do you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.genre_presets[preset_name] = values
                QMessageBox.information(self, "Success", f"Genre preset '{preset_name}' updated!")
            else:
                return

        # Otherwise, save as a custom preset
        else:
            self.custom_presets[preset_name] = values
            self.save_custom_presets()
            QMessageBox.information(self, "Success", f"Custom preset '{preset_name}' saved!")

        self.update_preset_dropdown()

    def save_genre_presets(self):
        """
        Save updated genre presets to a file.
        """
        with open(get_resource_path("presets/genre_presets.pkl"), "wb") as file:
            pickle.dump(self.genre_presets, file)

    def get_genre_presets(self):
        """
        Return a dictionary of pre-defined genre presets or load from file if available.
        """
        try:
            with open(get_resource_path("presets/genre_presets.pkl"), "rb") as file:
                return pickle.load(file)
        except (FileNotFoundError, EOFError, pickle.UnpicklingError):
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
                "R&B": [4, 3, 2, 1, 1, 1, 2, 2, 1, 0],
            }
        
    def get_default_genre_presets(self):
        """Return the original default genre presets."""
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
            "R&B": [4, 3, 2, 1, 1, 1, 2, 2, 1, 0],
        }

    def reset_selected_genre_preset(self):
        """
        Reset the selected genre preset to its original default value.
        """
        selected_preset = self.preset_dropdown.currentText()

        if selected_preset not in self.default_genre_presets:
            QMessageBox.warning(
                self, 
                "Error", 
                f"'{selected_preset}' is not a genre preset or does not have a default value."
            )
            return

        # Reset the selected preset
        self.genre_presets[selected_preset] = self.default_genre_presets[selected_preset]
        self.save_genre_presets()  # Save updated presets
        self.apply_preset_by_name(selected_preset)  # Apply the reset preset to sliders
        QMessageBox.information(
            self, 
            "Success", 
            f"'{selected_preset}' has been reset to its default value."
        )


    
    def closeEvent(self, event):
        """Handle actions on close."""
        reply = QMessageBox.question(
            self,
            "Confirm Exit",
            "Are you sure you want to exit the application?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No  # Default button
        )

        if reply == QMessageBox.Yes:
            self.save_genre_presets()  # Save presets before exiting
            event.accept()  # Accept the event to close the application
        else:
            event.ignore()  # Ignore the event to keep the application open

    def save_custom_presets(self):
        """Save custom presets to a file."""
        with open(get_resource_path("presets/custom_presets.pkl"), "wb") as file:
            pickle.dump(self.custom_presets, file)

    def load_custom_presets(self):
        with open(get_resource_path("presets/custom_presets.pkl"), "rb") as file:
            return pickle.load(file)

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
        self.bypass_button.setText("Equalizer: Enabled" if self.equalizer_enabled else "Equalizer: Bypassed")

    def apply_preset_by_name(self, preset_name):
        """Apply a preset by its name and update sliders."""
        if preset_name not in self.genre_presets and preset_name not in self.custom_presets:
            QMessageBox.warning(self, "Error", f"No preset found for: {preset_name}")
            return

        if preset_name in self.genre_presets:
            values = self.genre_presets[preset_name]
        else:
            values = self.custom_presets[preset_name]

        for slider, value in zip(self.sliders, values):
            slider.setValue(value)

        self.preset_dropdown.blockSignals(True)
        self.preset_dropdown.setCurrentText(preset_name)
        self.preset_dropdown.blockSignals(False)



    def audio_callback(self, in_data, frame_count, time_info, status):
        """Process audio data in real-time."""
        # Convert audio data to numpy array and reshape for stereo
        audio_data = np.frombuffer(in_data, dtype=np.int16).reshape(-1, 2)  # Stereo

        # Check if all gains are zero or if bypass mode is enabled
        if not self.equalizer_enabled or all(slider.value() == 0 for slider in self.sliders):
            return (in_data, pyaudio.paContinue)  # Bypass the processing

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
        input_device_index = None  # Ensure this is correct for your setup
        input_keywords = ["CABLE Output - TEST"]

        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            device_name = device_info['name']
            for keyword in input_keywords:
                if keyword.lower() in device_name.lower():
                    input_device_index = i
                    print(f"Selected Input Device: Index {i}: {device_name}")
                    break
            if input_device_index is not None:
                break

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

    def confirm_restart(self):
        """
        Show a confirmation dialog to restart the application.
        """
        reply = QMessageBox.question(
            self,
            "Confirm Restart",
            "Are you sure you want to restart the application? This will refresh the device list.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No  # Default to No
        )

        if reply == QMessageBox.Yes:
            self.restart_script()  # Restart the application

    def restart_script(self):
        """
        Restart the script to force reinitialization of PyAudio.
        """
        python = sys.executable  # Path to the Python interpreter
        os.execv(python, [python] + sys.argv)  # Restart the script with the same arguments

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

    # def refresh_spotify_login(self):
    #     """Refresh the Spotify login."""
    #     self.spotify.refresh_login()
    #     QMessageBox.information(self, "Refresh Login", "Spotify login refreshed successfully.")

    def load_artist_genres(self):
        """Load the artist-genre mapping from a file."""
        try:
            with open(get_resource_path("artist_genres.pkl"), "rb") as file:
                return pickle.load(file)
        except (FileNotFoundError, EOFError, pickle.UnpicklingError):
            return {}

    def save_artist_genres(self):
        """Save the artist-genre mapping to a file."""
        with open(get_resource_path("artist_genres.pkl"), "wb") as file:
            pickle.dump(self.artist_genres, file)
    
    def assign_genre_to_artist(self):
        """Assign a genre to an artist and validate before proceeding."""
        artist = self.artist_input.text().strip()
        genre = self.genre_input.text().strip()

        if not artist or not genre:
            QMessageBox.warning(self, "Error", "Both artist and genre fields must be filled.")
            return  # Exit early if inputs are invalid

        # Check if the genre preset exists before assigning
        if genre not in self.genre_presets and genre not in self.custom_presets:
            QMessageBox.warning(self, "Error", f"Preset '{genre}' does not exist.")
            return  # Exit early if the genre preset is invalid

        # Assign the genre to the artist
        self.artist_genres[artist] = genre
        self.save_artist_genres()

        # Clear fields after assigning
        self.artist_input.clear()
        self.genre_input.clear()

        QMessageBox.information(self, "Success", f"Assigned genre '{genre}' to artist '{artist}'.")



    def reset_genre_for_artist(self):
        """Reset the assigned genre for the current artist."""
        artist = self.artist_input.text().strip()

        if not artist:
            QMessageBox.warning(self, "Error", "No artist selected to reset.")
            return

        if artist in self.artist_genres:
            del self.artist_genres[artist]
            self.save_artist_genres()
            QMessageBox.information(self, "Success", f"Reset genre assignment for artist '{artist}'.")
        else:
            QMessageBox.warning(self, "Error", f"No genre assignment found for artist '{artist}'.")

        # Clear fields after resetting
        self.artist_input.clear()
        self.genre_input.clear()

