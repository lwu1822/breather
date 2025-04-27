# backend_runner.py

import threading
from pynput import keyboard
from fatigue_detector import KeyboardStats, kbd_on_event
from time import time, sleep


class FatigueMonitor(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)  # Daemon thread, dies with main app
        self.keyboard_stats = KeyboardStats()
        self._lock = threading.Lock()
        self._fatigue_history = []  # (timestamp, fatigue)
        self._running = True

        # Listener setup
        self.listener = keyboard.Listener(
            on_press=lambda k, i: kbd_on_event(k, True, self.keyboard_stats),
            on_release=lambda k, i: kbd_on_event(k, False, self.keyboard_stats),
        )

    def run(self):
        self.listener.start()

        while self._running:
            sleep(5)  # Every 5 seconds, sample fatigue
            with self._lock:
                fatigue = self.keyboard_stats.fatigue()
                self._fatigue_history.append((time(), fatigue))
                # Clean up old entries (>2 minutes ago)
                self._fatigue_history = [(t, f) for t, f in self._fatigue_history if t > time() - 120]

    def get_latest_fatigue(self) -> float:
        with self._lock:
            if not self._fatigue_history:
                return 0.0
            return self._fatigue_history[-1][1]

    def get_fatigue_sum(self) -> float:
        with self._lock:
            return sum(f for _, f in self._fatigue_history)

    def stop(self):
        self._running = False
        self.listener.stop()
