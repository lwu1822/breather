import sys
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import QTimer

def create_tray_app():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    base_pixmap = QPixmap("appIcon.png")  # Your static image

    tray = QSystemTrayIcon()
    tray.setIcon(QIcon(base_pixmap))
    tray.setVisible(True)
    tray.setToolTip("Breather")
    tray.show()  # <-- the icon must be visible before showMessage()

    # Tray menu
    menu = QMenu()
    show_action = menu.addAction("Show Message")
    menu.addSeparator()
    quit_action = menu.addAction("Quit")


    show_action.triggered.connect(lambda: tray.showMessage("Stress Level", "You're doing great!", QSystemTrayIcon.Information, 1000))
    quit_action.triggered.connect(app.quit)
    tray.setContextMenu(menu)

    tray.showMessage(
      "You seem stressed",
      "Maybe take a break?",
      QSystemTrayIcon.Information,
      5000
    )

    # Glow effect variables
    alpha = 0
    direction = 1  # 1 = fade in, -1 = fade out

    def update_glow():
        nonlocal alpha, direction

        # Update alpha value
        alpha += direction * 10
        if alpha >= 255:
            alpha = 255
            direction = -1
        elif alpha <= 50:
            alpha = 50
            direction = 1

        # Create glowing version
        glow_pixmap = QPixmap(base_pixmap.size())
        glow_pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

        painter = QPainter(glow_pixmap)
        painter.setOpacity(alpha / 255.0)
        painter.drawPixmap(0, 0, base_pixmap)
        painter.end()

        tray.setIcon(QIcon(glow_pixmap))

    # Timer to animate glow/fade
    timer = QTimer()
    timer.timeout.connect(update_glow)
    timer.start(100)  # Adjust speed here

    sys.exit(app.exec())

if __name__ == "__main__":
    create_tray_app()

# conditino to make fading in and out based on stress level (faster if more stressed, slower if less stressed)