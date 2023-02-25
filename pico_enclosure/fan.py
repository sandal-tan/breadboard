"""Interface with a 4-Pin PWM Fan."""

from machine import Pin, PWM  # pyright: ignore [reportMissingImports]

from .api import api
from .base import BaseDevice
from .logging import logger


class Fan(BaseDevice):
    """A 4-Pin PWM Fan.

    Args:
        name: A unique identifier for the fan. Will be used as an API path
        logger: A logger for the device to use
        pin: The GPIO pin on to which the fan signal is connected
        freq: The required PWM frequency of the fan
        idle: The default speed of the fan
        max_duty_cycle: The allowable maximum is 65535, tweak if fan does not turn off correctly.

    """

    def __init__(
        self,
        name: str,
        pin: int,
        freq: int = 25000,
        idle: int = 25,
        max_duty_cycle: int = 65530,
    ):
        super().__init__(name, None)
        self._pwm_fan = PWM(Pin(pin))
        self._speed_value = idle
        self.max_duty_cycle = max_duty_cycle
        self._pwm_fan.freq(freq)

        api.route(f"/{self.name}/on")(self.on)
        api.route(f"/{self.name}/off")(self.off)
        api.route(f"/{self.name}/set")(self.set)

        self._set(self._speed_value)

    async def on(self):
        """Turn the fan on.

        Returns:
            The speed value of the fan.

        """
        self._set(self._speed_value)
        return self._speed_value

    async def off(self):
        """Turn off the fan.

        Returns:
            True

        """
        self._set(0)
        return True

    def _set(self, value: int):
        logger.debug("Set fan speed to %d", value)
        value = round((100 - value) / 100 * self.max_duty_cycle)

        self._pwm_fan.duty_u16(value)

    async def set(self, value: int):
        """Set the fan speed as a percentage.

        Args:
            value: The percentage (0-100) of speed that the fan should be set to

        Returns:
            The set speed value

        """
        self._speed_value = int(value)
        self._set(self._speed_value)
        return value
