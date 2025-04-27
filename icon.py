import sys
import platform
from PySide6.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
    QMenu,
    QWidget,
    QLabel,
    QVBoxLayout,
    QFrame,
    QProgressBar,
    QMessageBox,
)
from PySide6.QtGui import (
    QIcon,
    QPixmap,
    QPainter,
    QColor,
    QFont,
    QCursor,
    QPalette,
)
from PySide6.QtCore import QTimer, Qt
from desktop_notifier import DesktopNotifier
import asyncio
import threading
from backend_runner import FatigueMonitor


# # make sure app shows up in macOS
# if platform.system() == "Darwin":
#     try:
#         from Foundation import NSObject
#         from AppKit import NSApplication, NSApp, NSApplicationActivationPolicyRegular
#         app_mac = NSApplication.sharedApplication()
#         app_mac.setActivationPolicy_(NSApplicationActivationPolicyRegular)
#     except ImportError:
#         pass

# uses desktop_notifier library to display messages via terminal notifier
notifier = DesktopNotifier()

# prevent notification from being blocked by creating shared loop
event_loop = asyncio.new_event_loop()


def start_event_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


loop_thread = threading.Thread(
    target=start_event_loop, args=(event_loop,), daemon=True
)
loop_thread.start()


def create_tray_app():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Very cool: You can change the font and size of right clicking the icon
    # font = QFont("DejaVu Sans Mono", 12)
    # app.setFont(font)

    # --- Window setup ---
    stats_window = QWidget()
    stats_window.setWindowTitle("Breather Stats")
    stats_window.resize(320, 400)
    stats_window.setStyleSheet(
        """
        QWidget {
            background-color: #13122b;
            border-radius: 16px;
        }
    """
    )

    layout = QVBoxLayout()
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(15)

    title_label = QLabel("Stats")
    title_font = QFont("DejaVu Sans Mono", 18, QFont.Bold)
    title_label.setFont(title_font)
    title_label.setAlignment(Qt.AlignCenter)
    title_label.setStyleSheet("color: #d9b2ab;")
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
        font = QFont("DejaVu Sans Mono", 12)
        label.setFont(font)
        label.setText(f"<b style='color:#d9b2ab'>{bold_part}</b> {text}")
        label.setStyleSheet("font-size: 14px; color: #b2edd2;")
        return label


 

    # --- Load fatigue icons ---
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
    toggle_glow_action = menu.addAction(
        "Toggle Glow"
    )  # NEW: Toggle Glow button
    menu.addSeparator()

    # low_fatigue_action = menu.addAction("Set Low Fatigue (Green)")
    # medium_fatigue_action = menu.addAction("Set Medium Fatigue (Yellow)")
    # high_fatigue_action = menu.addAction("Set High Fatigue (Red)")

    menu.addSeparator()
    quit_action = menu.addAction("Quit")

    if not platform.system() == "Darwin":
        tray.setContextMenu(menu)

    def show_notification(title, message):
        async def send_notification():
            try:
                await notifier.send(title=title, message=message)
            except Exception as e:
                print(f"Notification failed: {e}")

        event_loop.call_soon_threadsafe(
            asyncio.create_task, send_notification()
        )

    # set fatigue level
    def set_low_fatigue():
        nonlocal base_pixmap, displaym
        tray.setIcon(QIcon(green_pixmap))
        base_pixmap = green_pixmap
        displaym = "You're doing great!"
        if is_glowing:
            timer.start(200)
        QTimer.singleShot(
            1000, lambda: show_notification("Fatigue Level", displaym)
        )

    def set_medium_fatigue():
        nonlocal base_pixmap, displaym
        tray.setIcon(QIcon(yellow_pixmap))
        base_pixmap = yellow_pixmap
        displaym = "Relax a little, you got this!"
        if is_glowing:
            timer.start(100)
        QTimer.singleShot(
            1000, lambda: show_notification("Fatigue Level", displaym)
        )

    def set_high_fatigue():
        nonlocal base_pixmap, displaym
        tray.setIcon(QIcon(red_pixmap))
        base_pixmap = red_pixmap
        displaym = "Maybe try taking a break?"
        if is_glowing:
            timer.start(50)
        QTimer.singleShot(
            1000, lambda: show_notification("You seem fatigued", displaym)
        )

    # low_fatigue_action.triggered.connect(set_low_fatigue)
    # medium_fatigue_action.triggered.connect(set_medium_fatigue)
    # high_fatigue_action.triggered.connect(set_high_fatigue)

    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.Trigger:  # Left click
            if stats_window.isVisible():
                stats_window.hide()
            else:
                stats_window.show()
                stats_window.raise_()
                stats_window.activateWindow()
        elif (
            reason == QSystemTrayIcon.Context and platform.system() == "Darwin"
        ):  # Right click
            menu.popup(QCursor.pos())  # Show menu manually

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
        else:
            timer.stop()
            if displaym == "You're doing great!":
                timer.start(200)
            elif displaym == "Relax a little, you got this!":
                timer.start(100)
            elif displaym == "Maybe try taking a break?":
                timer.start(50)
        is_glowing = not is_glowing

    toggle_glow_action.triggered.connect(toggle_glow)

    fatigue_monitor = FatigueMonitor()
    fatigue_monitor.start()

    fatigue_timer = QTimer()
    fatigue_timer.setInterval(500)  # .5 seconds

    last_level = None

    stat_labels = {}          # keep references here

    def make_stat(key, label, initial):
        ql = QLabel()
        ql.setFont(QFont("DejaVu Sans Mono", 12))
        ql.setStyleSheet("font-size: 14px; color: #b2edd2;")
        ql.setText(f"<b style='color:#d9b2ab'>{label}</b> {initial}")
        layout.addWidget(ql)
        stat_labels[key] = ql

    make_stat("wpm",       "Typing speed:",   "0 words/min")
    make_stat("accuracy",  "Accuracy:",       "–")
    make_stat("favkey",    "Most-pressed:",   "–")
    make_stat("active",    "Active typing:",  "0 min")
    make_stat("idle",      "Idle time:",      "0 min")

    layout.addWidget(divider())

    def update_fatigue_status():
        nonlocal last_level
        fatigue = fatigue_monitor.get_latest_fatigue()

        if fatigue >= 1.25:
            level = "high"
            if level != last_level:
                set_high_fatigue()
        elif fatigue >= 0.25:
            level = "medium"
            if level != last_level:
                set_medium_fatigue()
        else:
            level = "low"
            if level != last_level:
                set_low_fatigue()

        last_level = level

        total_fatigue = fatigue_monitor.get_fatigue_sum()
        if total_fatigue > 20:
            show_notification(
                "Consider taking a break!", "Your fatigue is building up!"
            )
        print(f"Fatigue: {fatigue:.2f} (Total: {total_fatigue:.2f})")

        wpm       = fatigue_monitor.get_wpm()     # replace with real calc
        print(fatigue_monitor.get_backspace_rate())
        accuracy  = fatigue_monitor.get_backspace_rate()
        fav_key   = "[Space]"
        active_m  = 45
        idle_m    = 5

        stat_labels["wpm"].setText(
            f"<b style='color:#d9b2ab'>Typing speed:</b> {wpm} words/min"
        )

        stat_labels["accuracy"].setText(
            f"<b style='color:#d9b2ab'>Accuracy:</b> {accuracy}"
        )
        stat_labels["favkey"].setText(
            f"<b style='color:#d9b2ab'>Most-pressed:</b> {fav_key}"
        )
        stat_labels["active"].setText(
            f"<b style='color:#d9b2ab'>Active typing:</b> {active_m} minutes"
        )
        stat_labels["idle"].setText(
            f"<b style='color:#d9b2ab'>Idle time:</b> {idle_m} minutes"
        )


    fatigue_timer.timeout.connect(update_fatigue_status)
    fatigue_timer.start()


    

    # typing_mood_label = QLabel("<b style='color:#d9b2ab'>Mood:</b> Focused")
    # typing_mood_label.setStyleSheet("font-size: 14px; color: #b2edd2;")
    # layout.addWidget(typing_mood_label)

    # suggested_break_label = QLabel(
    #     "<b style='color:#d9b2ab'>Break in:</b> 10 min"
    # )
    # suggested_break_label.setStyleSheet("font-size: 14px; color: #b2edd2;")
    # layout.addWidget(suggested_break_label)

    stats_window.setLayout(layout)

    # break_progress = QProgressBar()
    # break_progress.setRange(0, 20)  # 600 seconds = 10 minutes
    # break_progress.setValue(0)
    # break_progress.setStyleSheet(
    #     """
    #     QProgressBar {
    #         border: 2px solid #b2edd2;
    #         border-radius: 5px;
    #         background-color: #13122b;
    #         text-align: center;
    #         color: #ffffff;
    #         font-weight: bold;
    #     }
    #     QProgressBar::chunk {
    #         background-color: #d9b2ab;
    #     }
    # """
    # )
    # layout.addWidget(break_progress)

    # FUTURE PROGRESS: PROGRESS BAR FOR WORK/BREAK

    # break_time_seconds = 20  # 10 minutes
    # elapsed_seconds = 0

    # progress_timer = QTimer()
    # progress_timer.setInterval(1000)  # 1 second
    # progress_timer.start()

    # is_work_mode = True
    # work_time_seconds = 20  # (example) 10 minutes work
    # break_time_seconds = 10  # (example) 5 minutes break
    # current_cycle_seconds = work_time_seconds

    # def update_break_progress():
    #     nonlocal elapsed_seconds, is_work_mode, current_cycle_seconds
    #     elapsed_seconds += 1
    #     break_progress.setValue(elapsed_seconds)

    #     minutes_remaining = max(
    #         (current_cycle_seconds - elapsed_seconds) // 60, 0
    #     )
    #     if is_work_mode:
    #         suggested_break_label.setText(
    #             f"<b style='color:#d9b2ab'>Break in:</b> {minutes_remaining} min"
    #         )
    #     else:
    #         suggested_break_label.setText(
    #             f"<b style='color:#d9b2ab'>Work resumes in:</b> {minutes_remaining} min"
    #         )

    #     if elapsed_seconds >= current_cycle_seconds:
    #         elapsed_seconds = 0
    #         if is_work_mode:
    #             # Finished work session
    #             elapsed_seconds = 0
    #             # Ask the user if they want to start break

    #             msg_box = QMessageBox(stats_window)
    #             msg_box.setWindowTitle("Start Break?")
    #             msg_box.setText(
    #                 "You've finished your work session!\nStart your break now?"
    #             )
    #             msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

    #             # Full style sheet for entire QMessageBox (background, button)
    #             msg_box.setStyleSheet(
    #                 """
    #                 QMessageBox {
    #                     background-color: #13122b;
    #                 }
    #                 QLabel {
    #                     color: #b2edd2;
    #                     font-size: 14px;
    #                     font-family: 'DejaVu Sans Mono';
    #                 }
    #                 QPushButton {
    #                     background-color: #d9b2ab;
    #                     color: #13122b;
    #                     padding: 6px 12px;
    #                     border-radius: 6px;
    #                     font-weight: bold;
    #                 }
    #                 QPushButton:hover {
    #                     background-color: #b2edd2;
    #                     color: #13122b;
    #                 }
    #             """
    #             )

    #             reply = msg_box.exec()

    #             if reply == QMessageBox.Yes:
    #                 is_work_mode = False
    #                 current_cycle_seconds = break_time_seconds
    #                 break_progress.setRange(0, current_cycle_seconds)
    #                 break_progress.setValue(0)
    #                 break_progress.setStyleSheet(
    #                     """
    #                     QProgressBar {
    #                         border: 2px solid #d9b2ab;
    #                         border-radius: 5px;
    #                         background-color: #13122b;
    #                         text-align: center;
    #                         color: #ffffff;
    #                         font-weight: bold;
    #                     }
    #                     QProgressBar::chunk {
    #                         background-color: #b2edd2;
    #                     }
    #                 """
    #                 )
    #                 show_notification(
    #                     "Break Time!", "Relax and breathe for a bit!"
    #                 )
    #             else:
    #                 # If user says No, reset to new work session
    #                 is_work_mode = True
    #                 current_cycle_seconds = work_time_seconds
    #                 break_progress.setRange(0, current_cycle_seconds)
    #                 break_progress.setValue(0)
    #         else:
    #             # Switching to Break Mode
    #             msg_box = QMessageBox(stats_window)
    #             msg_box.setWindowTitle("End Break?")
    #             msg_box.setText("Break's over! Ready to work again?")
    #             msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

    #             # Full style sheet for entire QMessageBox (background, button)
    #             msg_box.setStyleSheet(
    #                 """
    #                 QMessageBox {
    #                     background-color: #13122b;
    #                 }
    #                 QLabel {
    #                     color: #b2edd2;
    #                     font-size: 14px;
    #                     font-family: 'DejaVu Sans Mono';
    #                 }
    #                 QPushButton {
    #                     background-color: #d9b2ab;
    #                     color: #13122b;
    #                     padding: 6px 12px;
    #                     border-radius: 6px;
    #                     font-weight: bold;
    #                 }
    #                 QPushButton:hover {
    #                     background-color: #b2edd2;
    #                     color: #13122b;
    #                 }
    #             """
    #             )

    #             reply = msg_box.exec()

    #             if reply == QMessageBox.Yes:
    #                 is_work_mode = True
    #                 current_cycle_seconds = work_time_seconds
    #                 break_progress.setRange(0, current_cycle_seconds)
    #                 break_progress.setValue(0)
    #                 break_progress.setStyleSheet(
    #                     """
    #                     QProgressBar {
    #                         border: 2px solid #d9b2ab;
    #                         border-radius: 5px;
    #                         background-color: #13122b;
    #                         text-align: center;
    #                         color: #ffffff;
    #                         font-weight: bold;
    #                     }
    #                     QProgressBar::chunk {
    #                         background-color: #b2edd2;
    #                     }
    #                 """
    #                 )
    #                 show_notification("Work Time!", "Time to grind!")
    #             else:
    #                 # If user says No, reset to new work session
    #                 is_work_mode = False
    #                 current_cycle_seconds = break_time_seconds
    #                 break_progress.setRange(0, current_cycle_seconds)
    #                 break_progress.setValue(0)

    #         break_progress.setRange(0, current_cycle_seconds)
    #         break_progress.setValue(0)

    # progress_timer.timeout.connect(update_break_progress)

    def quit_app():
        fatigue_monitor.stop()
        app.quit()

    # connect to dropdown menu
    show_action.triggered.connect(
        lambda: show_notification("Fatigue Level", displaym)
    )
    quit_action.triggered.connect(quit_app)

    # welcome message
    QTimer.singleShot(
        1000, lambda: show_notification("Breather", "Welcome to Breather!")
    )

    sys.exit(app.exec())


if __name__ == "__main__":
    create_tray_app()
