"""Interact with an LED strip inside the enclosure."""
from time import time, sleep_ms
import uasyncio as asyncio  # pyright: ignore [reportMissingImports]

from machine import Pin  # pyright: ignore [reportMissingImports]
from neopixel import NeoPixel  # pyright: ignore [reportMissingImports]

from .api import api
from .base import BaseDevice

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
        brightness = round(int(brightness) / 100)
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
        return True

    async def on(self):
        """Turn the LED strip on, restoring it to the previously set values."""
        for led, colors in self._state.items():
            self._np[led] = colors
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


class _OnboardLED(BaseDevice):
    """Control the Pico's onboard LED."""

    def __init__(self):
        self._led = Pin("LED", Pin.OUT)
        self._last_blink_time = 0

    async def blink(self, *pulses, blinks: int, time_between: int):
        """Blink the onboard LED at a given frequency.

        Args:
            pulses: A collection of on-off timings representing the blink
            blink: The number of time to flash defined by ``pulses``
            time_between: How long before the LED can be blinked again

        """
        current = time()
        if current - self._last_blink_time > time_between:
            self._last_blink_time = current
            for _ in range(blinks):
                for on_time, off_time in pulses:
                    self._led.value(1)
                    sleep_ms(on_time)
                    self._led.value(0)
                    sleep_ms(off_time)

    async def _loop(self):
        await self.blink(
            (100, 50),
            (100, 50),
            (100, 50),
            blinks=3,
            time_between=10,
        )
