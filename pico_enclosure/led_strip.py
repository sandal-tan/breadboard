"""Interact with an LED strip inside the enclosure."""
from time import sleep_ms

from machine import Pin
from neopixel import NeoPixel

DELAY = 500


class LEDStrip:
    """A NeoPixel LED Strip.

    Args:
        pin: The pin to which the LED strip is connteted.
        led_count: The number of LEDs in the strip

    """

    def __init__(self, pin: int, led_count: int, blacklist: list[int] = None):
        self._length = led_count
        self._np = NeoPixel(Pin(pin), led_count)
        self._state = [(0, 0, 0)] * len(self)
        self.blacklist = blacklist or []

    def fill(self, red: int, green: int, blue: int, brightness: float = 1):
        """Fill the LED with a single color.

        Args:
            red: The brightness value for the red channel (0-255)
            green: The brightness value for the green channel (0-255)
            blue: The brightness value for the blue channel (0-255)
            brightness: A relative brightness scaling across all channels (0-100)

        """
        color_tuple = [round(e * brightness) for e in (red, green, blue)]
        for idx in range(len(self)):
            if idx in self.blacklist:
                continue
            self._np[idx] = color_tuple
            self._state[idx] = color_tuple
        self._np.write()
        sleep_ms(DELAY)

    def gradient(self, start, end, brightness: float = 1):
        ranges = [
            range(
                start[idx],
                end[idx],
                round(abs(start[idx] - end[idx]) / len(self)) * -1
                if start[idx] > end[idx]
                else 1,
            )
            for idx in range(3)
        ]

        for idx, rgb in enumerate(zip(*ranges)):
            if idx in self.blacklist:
                continue
            color_tuple = [round(c * brightness) for c in rgb]
            self._np[idx] = color_tuple
            self._state[idx] = color_tuple
        self._np.write()
        sleep_ms(DELAY)

    def on(self):
        for idx, entry in enumerate(self._state):
            self._np[idx] = entry
        self._np.write()

    def off(self):
        for idx in range(len(self)):
            self._np[idx] = (0, 0, 0)
        self._np.write()

    def __len__(self):
        return self._length
