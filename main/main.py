import sys
from PyQt5.QtWidgets import QApplication
from equalizer import EqualizerWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EqualizerWindow()
    window.show()
    sys.exit(app.exec_())