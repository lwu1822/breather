import ctypes
import sys
import platform
import os
import subprocess
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import QTimer

if platform.system() == "Darwin":
    try:
        from Foundation import NSObject
        from AppKit import NSApplication, NSApp, NSApplicationActivationPolicyRegular
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    except ImportError:
        pass

def create_tray_app():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    base_pixmap = QPixmap("appIcon.png")
    tray = QSystemTrayIcon(QIcon(base_pixmap))
    tray.setVisible(True)
    tray.setToolTip("Breather")

    menu = QMenu()
    show_action = menu.addAction("Show Message")
    quit_action = menu.addAction("Quit")
    tray.setContextMenu(menu)

    def show_notification(title, message):
        if platform.system() == "Darwin":
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(["osascript", "-e", script])
        else:
            tray.showMessage(title, message, QSystemTrayIcon.Information, 5000)

    QTimer.singleShot(1000, lambda: show_notification("You seem stressed", "Maybe take a break?"))
    show_action.triggered.connect(lambda: show_notification("Stress Level", "You're doing great!"))
    quit_action.triggered.connect(app.quit)

    alpha = 0
    direction = 1

    def update_glow():
        nonlocal alpha, direction
        alpha += direction * 10
        if alpha >= 255:
            alpha = 255
            direction = -1
        elif alpha <= 50:
            alpha = 50
            direction = 1

        glow_pixmap = QPixmap(base_pixmap.size())
        glow_pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(glow_pixmap)
        painter.setOpacity(alpha / 255.0)
        painter.drawPixmap(0, 0, base_pixmap)
        painter.end()

        tray.setIcon(QIcon(glow_pixmap))

    timer = QTimer()
    timer.timeout.connect(update_glow)
    timer.start(100)

    sys.exit(app.exec())

if __name__ == "__main__":
    create_tray_app()
