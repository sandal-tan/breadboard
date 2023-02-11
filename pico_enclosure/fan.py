"""Interface with a 4-Pin PWM Fan."""

from machine import Pin, PWM


class Fan:
    """A 4-Pin PWM Fan.

    Args:
        pin: The GPIO pin on to which the fan signal is conntect
        freq: The requied PWM frequence of the fan

    """

    def __init__(self, pin: int, freq: int = 25000):
        self._pwm_fan = PWM(Pin(pin))
        self._speed_value = 0

    def on(self):
        self._set(self._speed_value)

    def off(self):
        self._set(0)

    def _set(self, value: int):
        self._pwm_fan.duty_u16(round((100 - value) / 100 * 65535))

    def set(self, value: int):
        self._speed_value = value
        self._set(self._speed_value)
