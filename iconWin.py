import sys
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
import os

def create_tray_app():
    app = QApplication(sys.argv)

    # Make sure the app keeps running even without a visible window
    app.setQuitOnLastWindowClosed(False)

    # Set up the icon (you can replace it with your own .png or .ico file)
    icon_path = r"appIcon.png"  # Update with correct Windows path
    if not os.path.exists(icon_path):
        print(f"Icon file not found: {icon_path}")
        return  # Exit if the icon file doesn't exist
    
    icon = QIcon(icon_path)

    # Create the tray icon
    tray = QSystemTrayIcon()
    tray.setIcon(icon)
    tray.setVisible(True)
    tray.setToolTip("My App")
    tray.show()  # <-- the icon must be visible before showMessage()

    # Create the menu
    menu = QMenu()

    show_action = QAction("Show Message")
    quit_action = QAction("Quit")

    menu.addAction(show_action)
    menu.addSeparator()
    menu.addAction(quit_action)

    tray.setContextMenu(menu)

    # Connect actions
    show_action.triggered.connect(lambda: tray.showMessage("Stress Level", "You're doing great!", QSystemTrayIcon.Information, 1000))
    quit_action.triggered.connect(app.quit)

    tray.showMessage(
      "You seem stressed",
      "Maybe take a break?",
      QSystemTrayIcon.Information,
      5000
    )

    # Start the application loop
    sys.exit(app.exec())

if __name__ == "__main__":
    create_tray_app()
