import sys
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from time import sleep
from equalizer import EqualizerWindow  # Adjust the import based on your structure

class AnimatedSplashScreen(QSplashScreen):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loading...")
        self.setGeometry(300, 300, 400, 200)  # Centered and adjusted size

        # Load and set the PNG image with a clear background
        splash_pix = QPixmap("loading.png")  # Replace with your image path
        self.setPixmap(splash_pix)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Show splash screen with the image
    splash = AnimatedSplashScreen()
    splash.show()

    # Simulate loading time
    sleep(1)  # Simulate a delay for loading resources

    # Initialize your main window here
    window = EqualizerWindow()
    window.show()

    splash.finish(window)  # Close splash screen when main window is ready
    sys.exit(app.exec_())