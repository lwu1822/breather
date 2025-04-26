import sys
import platform
import os
import subprocess
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QWidget, QLabel, QVBoxLayout, QFrame
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import QTimer, Qt
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

    # --- Window setup ---
    stats_window = QWidget()
    stats_window.setWindowTitle("Breather Stats")
    stats_window.resize(320, 400)
    stats_window.setStyleSheet("""
        QWidget {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #f0f4f8, stop:1 #d9e2ec);
            border-radius: 16px;
        }
    """)

    layout = QVBoxLayout()
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(15)

    title_label = QLabel("Keyboard Stress Stats")
    title_font = QFont("Arial", 20, QFont.Bold)
    title_label.setFont(title_font)
    title_label.setAlignment(Qt.AlignCenter)
    title_label.setStyleSheet("color: #102a43;")
    layout.addWidget(title_label)

    def divider():
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #bcccdc; background-color: #bcccdc;")
        return line

    layout.addWidget(divider())

    def stat_label(text, bold_part):
        label = QLabel()
        label.setText(f"<b style='color:#243b53'>{bold_part}</b> {text}")
        label.setStyleSheet("font-size: 14px; color: #334e68;")
        return label

    stats = [
        ("words/min", "72"),
        ("chars/min", "320"),
        ("accuracy", "95%"),
        ("most pressed", "[Space]"),
        ("active typing", "42 min"),
        ("idle time", "5 min"),
    ]

    for text, value in stats:
        layout.addWidget(stat_label(text, value))

    layout.addWidget(divider())

    typing_mood_label = QLabel("<b style='color:#243b53'>Mood:</b> Focused 🧘")
    typing_mood_label.setStyleSheet("font-size: 14px; color: #334e68;")
    layout.addWidget(typing_mood_label)

    suggested_break_label = QLabel("<b style='color:#243b53'>Break in:</b> 10 min ⏳")
    suggested_break_label.setStyleSheet("font-size: 14px; color: #334e68;")
    layout.addWidget(suggested_break_label)

    stats_window.setLayout(layout)

    # --- Load stress icons ---
    green_pixmap = QPixmap("images/green.png")
    yellow_pixmap = QPixmap("images/yellow.png")
    red_pixmap = QPixmap("images/red.png")

    green_icon = QIcon(green_pixmap)
    yellow_icon = QIcon(yellow_pixmap)
    red_icon = QIcon(red_pixmap)

    base_pixmap = green_pixmap
    displaym = "You're doing great!"

    tray = QSystemTrayIcon(QIcon(base_pixmap))
    tray.setVisible(True)
    tray.setToolTip("Breather")

    menu = QMenu()
    show_action = menu.addAction("Show Message")
    toggle_glow_action = menu.addAction("Toggle Glow")  # NEW: Toggle Glow button
    menu.addSeparator()

    low_stress_action = menu.addAction("Set Low Stress (Green)")
    medium_stress_action = menu.addAction("Set Medium Stress (Yellow)")
    high_stress_action = menu.addAction("Set High Stress (Red)")

    menu.addSeparator()
    quit_action = menu.addAction("Quit")
    tray.setContextMenu(menu)

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

    # --- Stress level functions ---
    def set_low_stress():
        nonlocal base_pixmap, displaym
        tray.setIcon(QIcon(green_pixmap))
        base_pixmap = green_pixmap
        displaym = "You're doing great!"
        if is_glowing:
            timer.start(200)
        QTimer.singleShot(1000, lambda: show_notification("Stress Level", displaym))

    def set_medium_stress():
        nonlocal base_pixmap, displaym
        tray.setIcon(QIcon(yellow_pixmap))
        base_pixmap = yellow_pixmap
        displaym = "Relax a little, you got this!"
        if is_glowing:
            timer.start(100)
        QTimer.singleShot(1000, lambda: show_notification("Stress Level", displaym))

    def set_high_stress():
        nonlocal base_pixmap, displaym
        tray.setIcon(QIcon(red_pixmap))
        base_pixmap = red_pixmap
        displaym = "Maybe try taking a break?"
        if is_glowing:
            timer.start(50)
        QTimer.singleShot(1000, lambda: show_notification("You seem stressed", displaym))

    low_stress_action.triggered.connect(set_low_stress)
    medium_stress_action.triggered.connect(set_medium_stress)
    high_stress_action.triggered.connect(set_high_stress)

    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.Trigger:  # Left click
            if stats_window.isVisible():
                stats_window.hide()
            else:
                stats_window.show()
                stats_window.raise_()
                stats_window.activateWindow()

    tray.activated.connect(on_tray_activated)

    # --- Glow / Fade logic ---
    alpha = 0
    direction = 1
    is_glowing = True  # Control fading state

    timer = QTimer()

    def update_fade():
        nonlocal alpha, direction

        alpha += direction * 10
        if alpha >= 255:
            alpha = 255
            direction = -1
        elif alpha <= 5:
            alpha = 50
            direction = 1

        glow_pixmap = QPixmap(base_pixmap.size())
        glow_pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(glow_pixmap)
        painter.setOpacity(alpha / 255.0)
        painter.drawPixmap(0, 0, base_pixmap)
        painter.end()

        tray.setIcon(QIcon(glow_pixmap))

    timer.timeout.connect(update_fade)
    timer.start(200)

    def toggle_glow():
        nonlocal is_glowing
        if is_glowing:
            timer.stop()
            tray.setIcon(QIcon(base_pixmap))  # Show static icon
        is_glowing = not is_glowing

    toggle_glow_action.triggered.connect(toggle_glow)

    # --- Connect menu actions ---
    show_action.triggered.connect(lambda: show_notification("Stress Level", displaym))
    quit_action.triggered.connect(app.quit)

    # Automatically display notification on start
    QTimer.singleShot(1000, lambda: show_notification("Breather", "Welcome to Breather!"))

    sys.exit(app.exec())


if __name__ == "__main__":
    create_tray_app()
