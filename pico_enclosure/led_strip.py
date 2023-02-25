"""Interact with an LED strip inside the enclosure."""
from time import time, sleep_ms
import uasyncio as asyncio  # pyright: ignore [reportMissingImports]

from machine import Pin  # pyright: ignore [reportMissingImports]
from neopixel import NeoPixel  # pyright: ignore [reportMissingImports]

from .api import api
from .base import BaseDevice
from .logging import logger

DELAY = 500

DEFAULT_COLOR = (0, 0, 0)


class NeoPixelStrip(BaseDevice):
    """A NeoPixel LED Strip.

    Args:
        name: A unique identifier for the LED strip
        pin: The pin to which the LED strip is connected.
        led_count: The number of LEDs in the strip
        blacklist: Indexes of LEDs to skip in the strip. Useful if you have a bad LED.

    """

    def __init__(
        self, name: str, pin: int, led_count: int, blacklist=None, default_color=None
    ):
        self.name = name
        self._length = led_count
        self._np = NeoPixel(Pin(pin), led_count)
        self._state = {v: default_color or DEFAULT_COLOR for v in range(len(self))}
        self.blacklist = blacklist or []

        api.route(f"/{self.name}/set")(self.set)
        api.route(f"/{self.name}/on")(self.on)
        api.route(f"/{self.name}/off")(self.off)

        asyncio.run(self.on())

    async def set(self, red: int, green: int, blue: int, brightness: int = 100):
        """Fill the LED with a single color.

        Args:
            red: The brightness value for the red channel (0-255)
            green: The brightness value for the green channel (0-255)
            blue: The brightness value for the blue channel (0-255)
            brightness: A relative brightness scaling across all channels (0-100)

        """
        brightness = int(brightness) / 100
        color_tuple = (
            round(int(red) * brightness),
            round(int(green) * brightness),
            round(int(blue) * brightness),
        )
        for idx in range(len(self)):
            if idx in self.blacklist:
                continue
            self._np[idx] = color_tuple
            self._state[idx] = color_tuple  # pyright: ignore [reportGeneralTypeIssues]
        self._np.write()
        await asyncio.sleep_ms(DELAY)

    async def on(self):
        """Turn the LED strip on, restoring it to the previously set values."""
        for led, colors in self._state.items():
            self._np[led] = colors
        self._np.write()

    async def off(self):
        """Turn off the LED strip."""
        for idx in range(len(self)):
            self._np[idx] = (0, 0, 0)
        self._np.write()

    def __len__(self):
        return self._length


class _OnboardLED(BaseDevice):
    """Control the Pico's onboard LED."""

    def __init__(self):
        self._led = Pin("LED", Pin.OUT)

    async def _loop(self):
        while True:
            self._led.value(1)
            await asyncio.sleep(1)
            self._led.value(0)
            await asyncio.sleep(1)
