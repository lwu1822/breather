from collections import deque
from time import time

from pynput import keyboard


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


class DataQueue(deque):
    def __init__(self, max_time: float = 30):
        super().__init__()
        self.max_time = max_time

    def clean(self, t: float):
        while self and self[0][0] < t - self.max_time:
            self.popleft()

    def push(self, event: DataEvent):
        self.clean(event[0])
        self.append(event)

    def katz_fd(self):
    """
    Compute the Katz fractal dimension of the data.
    Returns NaN for length < 2.
    """
    N = len(x)
    if N < 2:
        return float('nan')

    # 1) total curve length L
    L = 0.0
    for i in range(N-1):
        diff = x[i+1] - x[i]
        L += math.hypot(1, diff)       # sqrt(1 + diff^2)

    # 2) maximum distance from the first point
    d_max = 0.0
    x0 = x[0]
    for i, xi in enumerate(x):
        d = math.hypot(i, xi - x0)    # sqrt(i^2 + (xi-x0)^2)
        if d > d_max:
            d_max = d

    # 3) Katz dimension
    return math.log(N) / math.log(N * d_max / L)

    @property
    def mean(self) -> float:
        self.clean(time())
        if not self:
            return 0
        # print('  ', len(self))
        return sum(x[1] for x in self) / len(self)

    @property
    def std(self) -> float:
        mean = self.mean
        if not self:
            return 0
        return (sum((x[1] - mean) ** 2 for x in self) / len(self)) ** 0.5


class KeyboardStats:
    def __init__(self):
        self.unreleased: dict[KeyType, KeyboardEvent] = {}

        # times of all key events
        self.key_times: DataQueue[DataEvent] = DataQueue()
        # key press times
        self.press_times: DataQueue[DataEvent] = DataQueue()
        # key release times
        self.release_times: DataQueue[DataEvent] = DataQueue()
        # time between key press and release of the same key
        self.hold_times: DataQueue[DataEvent] = DataQueue()
        # backspace key event times (press and release)
        self.backspace_times: DataQueue[DataEvent] = DataQueue()
        # time between key release and next key press
        self.flight_times: DataQueue[DataEvent] = DataQueue()
        # time between backspace and previous key event
        self.pre_correction_times: DataQueue[DataEvent] = DataQueue()
        # time between two key events
        self.latencies: DataQueue[DataEvent] = DataQueue()

    def push(self, event: KeyboardEvent):
        if self.key_times:
            self.latencies.push(
                (event.time, event.time - self.key_times[-1][0])
            )
        self.key_times.push((event.time, event.time))
        self.backspace_times.push(
            (event.time, event.key == keyboard.Key.backspace)
        )

        if event.pressed:
            self.unreleased[event.key] = event
            self.press_times.push((event.time, event.time))

            if (
                self.release_times
                and len(self.press_times) > 1
                and self.release_times[-1][0] > self.press_times[-2][0]
            ):  # last key event was a release
                self.flight_times.push(
                    (event.time, event.time - self.release_times[-1][0])
                )

            if event.key == keyboard.Key.backspace:
                if (
                    len(self.backspace_times) > 1
                    and self.backspace_times[-2][1] == 0
                ):
                    self.pre_correction_times.push(
                        (event.time, event.time - self.key_times[-2][0])
                    )
        else:
            self.release_times.push((event.time, event.time))

            press_event = self.unreleased.pop(event.key, None)
            if press_event:
                self.hold_times.push(
                    (event.time, event.time - press_event.time)
                )

    @property
    def backspace_rate(self) -> float:
        self.backspace_times.clean(time())
        if not self.backspace_times:
            return 0
        return sum(x[1] for x in self.backspace_times) / len(
            self.backspace_times
        )


def main():
    keyboard_stats = KeyboardStats()

    def on_event(key, pressed):
        if key is None:  # NOTE: should we handle unknown keys?
            return
        keyboard_stats.push(KeyboardEvent(key, pressed, time()))
        print(  # DEBUG
            keyboard_stats.latencies.mean,
            keyboard_stats.latencies.std,
        )

    # listener = keyboard.Listener(
    #     on_press=lambda k, i: on_event(k, True),
    #     on_release=lambda k, i: on_event(k, False),
    # )
    # listener.join()

    with keyboard.Listener(
        on_press=lambda k, i: on_event(k, True),
        on_release=lambda k, i: on_event(k, False),
    ) as listener:
        listener.join()

    # TODO: calculate stress


if __name__ == "__main__":
    main()
