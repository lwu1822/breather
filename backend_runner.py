# backend_runner.py

import threading
from pynput import keyboard
from fatigue_detector import KeyboardStats, kbd_on_event, DataQueue
from time import time


class FatigueMonitor(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)  # Daemon thread, dies with main app
        self.keyboard_stats = KeyboardStats()
        self._lock = threading.Lock()
        self._fatigue_history = DataQueue(max_time=120)
        self.SAMPLES_CUTOFF = 600

        self.listener = keyboard.Listener(
            on_press=lambda k, i: kbd_on_event(k, True, self.keyboard_stats),
            on_release=lambda k, i: kbd_on_event(k, False, self.keyboard_stats),
        )

    def start(self):
        self.listener.start()

    def get_latest_fatigue(self) -> float:
        with self._lock:
            # if not self._fatigue_history:
            #     return 0.0
            fatigue = self.keyboard_stats.fatigue()
            self._fatigue_history.push((time(), fatigue))
            return fatigue

    def get_fatigue_sum(self) -> float:
        with self._lock:
            return sum(f for _, f in self._fatigue_history)

    def get_wpm(self) -> float:
        with self._lock:
            return self.keyboard_stats.wpm()

    def get_wpm_lifetime(self) -> float:
        with self._lock:
            return (
                self.keyboard_stats.wpm_baseline.mean
                if self.keyboard_stats.wpm_baseline.n > self.SAMPLES_CUTOFF
                else float("nan")
            )

    def get_backspace_rate(self) -> float:
        with self._lock:
            return (1 - self.keyboard_stats.backspace_rate()) * 100

    def get_backspace_rate_lifetime(self) -> float:
        with self._lock:
            return (
                (1 - self.keyboard_stats.backspace_times.baseline.mean) * 100
                if (
                    self.keyboard_stats.backspace_times.baseline.n
                    > self.SAMPLES_CUTOFF
                )
                else float("nan")
            )

    def get_flight_time(self) -> float:
        with self._lock:
            return self.keyboard_stats.flight_times.mean()

    def get_flight_time_lifetime(self) -> float:
        with self._lock:
            return (
                self.keyboard_stats.flight_times.baseline.mean
                if self.keyboard_stats.flight_times.baseline.n
                > self.SAMPLES_CUTOFF
                else float("nan")
            )

    def get_hold_time(self) -> float:
        with self._lock:
            return self.keyboard_stats.hold_times.mean()

    def get_hold_time_lifetime(self) -> float:
        with self._lock:
            return (
                self.keyboard_stats.hold_times.baseline.mean
                if self.keyboard_stats.hold_times.baseline.n
                > self.SAMPLES_CUTOFF
                else float("nan")
            )

    def stop(self):
        self.listener.stop()
