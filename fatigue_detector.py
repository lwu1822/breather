import math

from collections import deque
from itertools import pairwise
from time import time

from pynput import keyboard


ALPHA = 1.5
CENTER = 0.0

# DEBUG
RAWS = []
FATIGUES = []


KeyType = keyboard.Key | keyboard.KeyCode
DataEvent = tuple[float, float]  # time, data


# key, pressed?, time
class KeyboardEvent:
    def __init__(
        self, key: keyboard.Key | keyboard.KeyCode, pressed: bool, t: float
    ):
        self.key: str = key
        self.pressed: bool = pressed
        self.time: float = t

    def __str__(self):
        return f"Key '{self.key}' {'pressed' if self.pressed else 'released'} at time {self.time}"

    def __repr__(self):
        return f"KeyboardEvent(key={self.key}, pressed={self.pressed}, time={self.time})"


class RunningStat:
    __slots__ = ("n", "mu", "M2")

    def __init__(self, pop_mu, pop_var, virtual_n=400):
        self.n = virtual_n  # population as virtual samples
        self.mu = pop_mu
        self.M2 = pop_var * virtual_n  # Σ(x-μ)² from the virtual prior

    def update(self, x: float):
        self.n += 1
        delta = x - self.mu
        self.mu += delta / self.n
        self.M2 += delta * (x - self.mu)

    @property
    def mean(self):
        return self.mu

    @property
    def std(self):
        return math.sqrt(self.M2 / max(self.n - 1, 1))


class DataQueue(deque):
    def __init__(
        self,
        baseline_mu: float | None = None,
        baseline_var: float | None = None,
        max_time: float = 30,
    ):
        super().__init__()
        self.max_time = max_time

        self.has_baseline = baseline_mu is not None
        if self.has_baseline:
            self.baseline = RunningStat(baseline_mu, baseline_var)

    def clean(self, t: float):
        while self and self[0][0] < t - self.max_time:
            self.popleft()

    def push(self, event: DataEvent):
        self.clean(event[0])
        self.append(event)
        if self.has_baseline:
            self.baseline.update(event[1])

    def katz_fd(self):
        """
        Compute the Katz fractal dimension of the data.
        Returns NaN for length < 2.
        """
        N = len(self)
        if N < 2:
            return float("nan")

        # 1) total curve length L
        L = sum(
            math.hypot(b[0] - a[0], b[1] - a[1]) for (a, b) in pairwise(self)
        )
        # print("length", L)  # DEBUG

        # 2) maximum distance from the first point
        t0, x0 = self[0]
        d_max = max(math.hypot(t - t0, x - x0) for t, x in self)
        # print("max dist", d_max)  # DEBUG

        # 3) Katz dimension
        # print("len", N)  # DEBUG
        return math.log(N) / math.log(N * d_max / L)

    def mean(self) -> float:
        self.clean(time())
        if not self:
            return 0
        return sum(x[1] for x in self) / len(self)

    def var(self) -> float:
        mean = self.mean()
        if not self:
            return 0
        return sum((x[1] - mean) ** 2 for x in self) / len(self)

    def std(self) -> float:
        return math.sqrt(self.var())

    def mean_zscore(self) -> float:
        if not self.has_baseline:
            raise ValueError("No baseline set")
        return (self.mean() - self.baseline.mean) / self.baseline.std

    def std_zscore(self) -> float:
        if not self.has_baseline:
            raise ValueError("No baseline set")
        return (self.std() - self.baseline.std) / self.baseline.std


class KeyboardStats:
    def __init__(self):
        self.num_events: int = 0
        self.unreleased: dict[KeyType, KeyboardEvent] = {}

        # times of all key events
        self.key_times: DataQueue[DataEvent] = DataQueue()
        # key press times
        self.press_times: DataQueue[DataEvent] = DataQueue()
        # key release times
        self.release_times: DataQueue[DataEvent] = DataQueue()
        # time between key press and release of the same key
        self.hold_times: DataQueue[DataEvent] = DataQueue(0.110, 0.035**2)
        # backspace key event times (press and release)
        self.backspace_times: DataQueue[DataEvent] = DataQueue(0.015, 0.010**2)
        # time between key release and next key press
        self.flight_times: DataQueue[DataEvent] = DataQueue(0.120, 0.050**2)
        # time between backspace and previous key event
        self.pre_correction_times: DataQueue[DataEvent] = DataQueue(
            0.180, 0.060**2
        )
        # time between two key events
        self.latencies: DataQueue[DataEvent] = DataQueue()
        self.wpm_baseline = RunningStat(70, 20**2)

    def push(self, event: KeyboardEvent):
        self.num_events += 1
        if self.key_times:
            self.latencies.push(
                (event.time, event.time - self.key_times[-1][0])
            )
        self.key_times.push((event.time, event.time))
        self.wpm_baseline.update(self.wpm())

        if event.pressed:
            self.unreleased[event.key] = event
            self.press_times.push((event.time, event.time))

            if (
                self.release_times
                and len(self.press_times) > 1
                and self.release_times[-1][0] > self.press_times[-2][0]
            ):  # last key event was a release
                flight_time = event.time - self.release_times[-1][0]
                if flight_time < 1:  # not just a long pause
                    self.flight_times.push((event.time, flight_time))

            if event.key == keyboard.Key.backspace:
                if (
                    len(self.backspace_times) > 1
                    and len(self.key_times) > 1
                    and self.backspace_times[-2][1] == 0
                ):
                    pre_correction_time = event.time - self.key_times[-2][0]
                    self.pre_correction_times.push(
                        (event.time, pre_correction_time)
                    )
                    self.backspace_times.push((event.time, 1))
                else:
                    self.backspace_times.push((event.time, 0))
            else:
                self.backspace_times.push((event.time, 0))
        else:
            self.release_times.push((event.time, event.time))

            press_event = self.unreleased.pop(event.key, None)
            if press_event:
                hold_time = event.time - press_event.time
                if hold_time < 0.5:  # not just holding the key down
                    self.hold_times.push((event.time, hold_time))

    def backspace_rate(self) -> float:
        self.backspace_times.clean(time())
        if not self.backspace_times:
            return 0
        return sum(x[1] for x in self.backspace_times) / len(
            self.backspace_times
        )

    def wpm(self) -> float:
        self.press_times.clean(time())
        if len(self.press_times) < 2:
            return 0
        i_actual = 0
        for i, (t1, t2) in enumerate(pairwise(self.press_times)):
            if t2[0] - t1[0] > 5:  # long pause
                i_actual = i

        if i_actual == 0:
            res = (
                len(self.press_times)
                / (self.press_times[-1][0] - self.press_times[0][0])
                * 60
                / 5  # 5 chars per word
            )
        else:
            if len(self.press_times) - i_actual < 2:
                return 0
            res = (
                len(self.press_times)
                / (self.press_times[-1][0] - self.press_times[i_actual][0])
                * 60
                / 5  # 5 chars per word
            )
        # print("WPM:", res)  # DEBUG
        return res

    def wpm_zscore(self) -> float:
        if not self.press_times:
            return 0
        return (self.wpm() - self.wpm_baseline.mean) / self.wpm_baseline.std

    def fatigue(self) -> float:
        # print("Fatigue:")  # DEBUG
        # print("            wpm:", self.wpm_zscore())  # DEBUG
        # print("     error rate:", self.backspace_times.mean_zscore())  # DEBUG
        # print("      hold time:", self.hold_times.mean_zscore())  # DEBUG
        # print("    flight time:", self.flight_times.mean_zscore())  # DEBUG
        total = (
            self.flight_times.mean_zscore()
            + self.hold_times.mean_zscore()
            + self.backspace_times.mean_zscore()
            - self.wpm_zscore()
        )
        # print("          total:", total)  # DEBUG
        return total


def kbd_on_event(key, pressed, kbd_stats_obj):
    # nonlocal mn, mx

    if key is None:  # NOTE: should we handle unknown keys?
        return
    kbd_stats_obj.push(KeyboardEvent(key, pressed, time()))

    # keyboard_stats.calculate_fatigue()
    # mn, mx = min(mn, s), max(mx, s)
    # print(f"Stress: {s:.2f} ({mn:.2f}, {mx:.2f})")


def main():
    keyboard_stats = KeyboardStats()

    # mn, mx = 1, 0
    # start_time = time()

    listener = keyboard.Listener(
        on_press=lambda k, i: kbd_on_event(k, True, keyboard_stats),
        on_release=lambda k, i: kbd_on_event(k, False, keyboard_stats),
    )
    listener.join()

    # while True:
    #     # poll
    #     fatigue = keyboard_stats.fatigue()
    #     __import__('time').sleep(5)

    # try:
    #     with keyboard.Listener(
    #         on_press=lambda k, i: on_event(k, True),
    #         on_release=lambda k, i: on_event(k, False),
    #     ) as listener:
    #         listener.join()
    # except KeyboardInterrupt:
    #     print("Listener stopped")

    # from matplotlib import pyplot as plt

    # print("Plotting ...")

    # plt.figure(figsize=(12, 6))

    # # Plot for RAWS
    # plt.subplot(1, 2, 1)
    # plt.hist(RAWS, bins=25, color="blue")
    # plt.title("Raw Stress Distribution")
    # plt.xlabel("Raw Stress")
    # plt.ylabel("Frequency")

    # # Plot for FATIGUES
    # plt.subplot(1, 2, 2)
    # plt.hist(FATIGUES, bins=25, color="green")
    # plt.title("Fatigue Distribution")
    # plt.xlabel("Fatigue")
    # plt.ylabel("Frequency")

    # plt.tight_layout()
    # plt.show()


if __name__ == "__main__":
    main()
