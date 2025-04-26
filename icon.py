import sys
import platform
import os
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import QTimer
from desktop_notifier import DesktopNotifier, Urgency
import asyncio
import threading

# make sure app shows up in macOS
if platform.system() == "Darwin":
    try:
        from Foundation import NSObject
        from AppKit import NSApplication, NSApp, NSApplicationActivationPolicyRegular
        app_mac = NSApplication.sharedApplication()
        app_mac.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    except ImportError:
        pass

# uses desktop_notifier library to display messages via terminal notifier
notifier = DesktopNotifier()

# prevent notification from being blocked by creating shared loop
event_loop = asyncio.new_event_loop()
def start_event_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

loop_thread = threading.Thread(target=start_event_loop, args=(event_loop,), daemon=True)
loop_thread.start()

def create_tray_app():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # load in icon
    base_pixmap = QPixmap("appIcon.png")
    tray = QSystemTrayIcon(QIcon(base_pixmap))
    tray.setVisible(True)
    tray.setToolTip("Breather")
    tray.show()

    # menubar options
    menu = QMenu()
    show_action = menu.addAction("Show Message")
    quit_action = menu.addAction("Quit")
    tray.setContextMenu(menu)

    # display notification
    def show_notification(title, message):
        async def send_notification():
            try:
                await notifier.send(
                    title=title,
                    message=message
                )
            except Exception as e:
                print(f"Notification failed: {e}")

        event_loop.call_soon_threadsafe(asyncio.create_task, send_notification())


    # automatically display notification
    QTimer.singleShot(1000, lambda: show_notification("You seem stressed", "Maybe take a break?"))

    # Connect menu actions
    show_action.triggered.connect(lambda: show_notification("Stress Level", "You're doing great!"))
    quit_action.triggered.connect(app.quit)

    # icon glowing/fading effect
    alpha = 0
    direction = 1

    def update_fade():
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
    timer.timeout.connect(update_fade)
    timer.start(100)

    sys.exit(app.exec())

if __name__ == "__main__":
    create_tray_app()
