"""Interact with an LED strip inside the enclosure."""
import uasyncio as asyncio  # pyright: ignore [reportMissingImports]

from machine import Pin  # pyright: ignore [reportMissingImports]
from neopixel import NeoPixel  # pyright: ignore [reportMissingImports]

from .api import api

DELAY = 500


class LEDStrip:
    """A NeoPixel LED Strip.

    Args:
        name: A unique identifier for the LED strip
        pin: The pin to which the LED strip is connected.
        led_count: The number of LEDs in the strip
        blacklist: Indexes of LEDs to skip in the strip

    """

    def __init__(self, name: str, pin: int, led_count: int, blacklist=None):
        self.name = name
        self._length = led_count
        self._np = NeoPixel(Pin(pin), led_count)
        self._state = {v: (0, 0, 0) for v in range(len(self))}
        self.blacklist = blacklist or []

        api.route(f"/{self.name}/fill")(self.fill)
        api.route(f"/{self.name}/on")(self.on)
        api.route(f"/{self.name}/off")(self.off)

    async def fill(self, red: int, green: int, blue: int, brightness: float = 1):
        """Fill the LED with a single color.

        Args:
            red: The brightness value for the red channel (0-255)
            green: The brightness value for the green channel (0-255)
            blue: The brightness value for the blue channel (0-255)
            brightness: A relative brightness scaling across all channels (0-100)

        """
        if not isinstance(brightness, (float, int)):
            brightness = float(brightness)
        color_tuple = (
            round(red * brightness),
            round(green * brightness),
            round(blue * brightness),
        )
        for idx in range(len(self)):
            if idx in self.blacklist:
                continue
            self._np[idx] = color_tuple
            self._state[idx] = color_tuple  # pyright: ignore [reportGeneralTypeIssues]
        self._np.write()
        await asyncio.sleep_ms(DELAY)
        return True

    async def on(self):
        """Turn the LED strip on, restoring it to the previously set values."""
        for idx, entry in enumerate(self._state):
            self._np[idx] = entry
        self._np.write()
        return True

    async def off(self):
        """Turn off the LED strip."""
        for idx in range(len(self)):
            self._np[idx] = (0, 0, 0)
        self._np.write()
        return True

    def __len__(self):
        return self._length
