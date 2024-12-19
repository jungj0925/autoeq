import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout,
                            QWidget, QHBoxLayout, QLabel, QFrame, QSlider, QMessageBox,
                            QComboBox, QDialog, QDialogButtonBox)
from PyQt5.QtCore import QTimer, Qt
from equalizer import Equalizer
import numpy as np
import sounddevice as sd

class DeviceSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Audio Devices")
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Input device selection
        input_label = QLabel("Input Device:")
        self.input_combo = QComboBox()
        self.populate_input_devices()
        layout.addWidget(input_label)
        layout.addWidget(self.input_combo)
        
        # Output device selection
        output_label = QLabel("Output Device:")
        self.output_combo = QComboBox()
        self.populate_output_devices()
        layout.addWidget(output_label)
        layout.addWidget(self.output_combo)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setMinimumWidth(300)
    
    def populate_input_devices(self):
        self.input_combo.addItem("Default", -1)
        for i, device in enumerate(sd.query_devices()):
            if device['max_input_channels'] > 0:
                name = device['name']
                if 'Stereo Mix' in name or 'What U Hear' in name:
                    name += " (Recommended for system audio)"
                self.input_combo.addItem(name, i)
    
    def populate_output_devices(self):
        self.output_combo.addItem("Default", -1)
        for i, device in enumerate(sd.query_devices()):
            if device['max_output_channels'] > 0:
                name = device['name']
                if 'Speakers' in name or 'Headphones' in name:
                    name += " (Recommended for playback)"
                self.output_combo.addItem(name, i)
    
    def get_selected_devices(self):
        input_idx = self.input_combo.currentData()
        output_idx = self.output_combo.currentData()
        return input_idx if input_idx != -1 else None, output_idx if output_idx != -1 else None

class EQBar(QFrame):
    def __init__(self, freq, initial_value=0):
        super().__init__()
        self.setMinimumWidth(30)
        self.setMinimumHeight(200)
        self.setFrameStyle(QFrame.Box)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Add slider for EQ control
        self.slider = QSlider(Qt.Vertical)
        self.slider.setRange(-12, 12)  # -12dB to +12dB
        self.slider.setValue(initial_value)
        self.slider.setTickPosition(QSlider.TicksBothSides)
        self.slider.setTickInterval(3)
        layout.addWidget(self.slider)
        
        # Value label
        self.value_label = QLabel('0 dB')
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)
        
        # Frequency label
        freq_label = QLabel(freq)
        freq_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(freq_label)
        
        # Update label when slider moves
        self.slider.valueChanged.connect(self.update_label)
        
    def update_label(self):
        self.value_label.setText(f'{self.slider.value()} dB')
        
    def get_value(self):
        return self.slider.value()
        
    def set_value(self, value):
        self.slider.setValue(int(value))
        self.update_label()

class EQVisualizer(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()
        self.bars = []
        
        # Create 10 vertical bars with labels
        frequencies = ['60', '170', '310', '600', '1k', '3k', '6k', '12k', '14k', '16k']
        for freq in frequencies:
            bar = EQBar(freq)
            self.layout.addWidget(bar)
            self.bars.append(bar)
            
            # Connect slider value changed to parent
            bar.slider.valueChanged.connect(self.on_slider_changed)
        
        self.setLayout(self.layout)
        
    def on_slider_changed(self):
        # Get all current values
        values = [bar.get_value() for bar in self.bars]
        # Emit these values to the equalizer
        if hasattr(self, 'parent') and hasattr(self.parent, 'equalizer'):
            self.parent.equalizer.set_manual_eq(values)

    def update_values(self, values):
        for bar, value in zip(self.bars, values):
            bar.set_value(value)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Equalizer")
        self.setGeometry(100, 100, 800, 500)

        # Main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Add EQ visualizer
        self.visualizer = EQVisualizer()
        self.visualizer.parent = self
        layout.addWidget(self.visualizer)

        # Control buttons layout
        button_layout = QHBoxLayout()
        
        # Add control buttons
        self.start_button = QPushButton("Start Auto EQ")
        self.start_button.clicked.connect(self.toggle_auto_eq)
        button_layout.addWidget(self.start_button)
        
        # Add device selection button
        self.device_button = QPushButton("Select Devices")
        self.device_button.clicked.connect(self.show_device_selection)
        button_layout.addWidget(self.device_button)
        
        # Add test tone button
        self.test_button = QPushButton("Play Test Tone")
        self.test_button.clicked.connect(self.play_test_tone)
        button_layout.addWidget(self.test_button)
        
        # Add reset button
        self.reset_button = QPushButton("Reset EQ")
        self.reset_button.clicked.connect(self.reset_eq)
        button_layout.addWidget(self.reset_button)
        
        layout.addLayout(button_layout)

        # Status label
        self.status_label = QLabel("Select audio devices to begin")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Initialize equalizer
        try:
            self.equalizer = Equalizer()
            # Don't show device list in console
            self.equalizer.list_devices = lambda: None
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            raise

        self.auto_eq_running = False
        
        # Setup timer for updating visualization
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_visualization)
        self.update_timer.setInterval(100)

    def show_device_selection(self):
        dialog = DeviceSelectionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            input_device, output_device = dialog.get_selected_devices()
            self.equalizer.set_devices(input_device, output_device)
            
            # Update status label
            if input_device is not None and output_device is not None:
                self.status_label.setText("Devices selected - Ready to start")
            else:
                self.status_label.setText("Using default devices - Ready to start")

    def play_test_tone(self):
        self.equalizer.play_test_sweep()

    def reset_eq(self):
        self.visualizer.update_values([0] * 10)
        self.equalizer.set_manual_eq([0] * 10)

    def toggle_auto_eq(self):
        if not self.auto_eq_running:
            self.equalizer.start_auto_eq()
            self.start_button.setText("Stop Auto EQ")
            self.auto_eq_running = True
            self.update_timer.start()
            self.device_button.setEnabled(False)
            self.status_label.setText("EQ Running")
        else:
            self.equalizer.stop_auto_eq()
            self.start_button.setText("Start Auto EQ")
            self.auto_eq_running = False
            self.update_timer.stop()
            self.device_button.setEnabled(True)
            self.status_label.setText("EQ Stopped")

    def update_visualization(self):
        if hasattr(self.equalizer, 'eq_values'):
            self.visualizer.update_values(self.equalizer.eq_values)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
