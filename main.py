import sys
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My First PySide6 App")
        label = QLabel("Hello, PySide6!")
        self.setCentralWidget(label)

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()