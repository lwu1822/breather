import sys
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QTimer

def create_tray_app():
    app = QApplication(sys.argv)

    # Make sure the app keeps running even without a visible window
    app.setQuitOnLastWindowClosed(False)

    # Set up the icon
    icon1 = QIcon("/Users/dumpling/Downloads/pfpq1.png")
    icon2 = QIcon("/Users/dumpling/Downloads/pfpq2.png")
  # Replace with your own .png or .ico file

    # Create the tray icon
    tray = QSystemTrayIcon()
    tray.setIcon(icon1)
    tray.setVisible(True)

    # Create the menu
    menu = QMenu()

    show_action = QAction("Show Message")
    quit_action = QAction("Quit")

    menu.addAction(show_action)
    menu.addSeparator()
    menu.addAction(quit_action)

    tray.setContextMenu(menu)

    # Connect actions
    show_action.triggered.connect(lambda: QMessageBox.information(None, "Hello", "This is a tray app!"))
    quit_action.triggered.connect(app.quit)

    def update_icon():
        tray.setIcon(icon2)
      
    timer = QTimer()
    timer.timeout.connect(update_icon)
    timer.setSingleShot(True)
    timer.start(10000)

    sys.exit(app.exec_())
    

if __name__ == "__main__":
    create_tray_app()