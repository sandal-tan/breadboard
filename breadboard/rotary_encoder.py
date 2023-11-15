"""Rotary Encoders."""

import asyncio
from machine import Pin # pyright: ignore [reportMissingImports]

from .base import StatefulDevice
from .api import api
from .logging import logger


class RotaryEncoder(StatefulDevice):
    """360deg interface rotary interface.

    Args:
        name: A reference for the rotary encoder
        pin_a: The pin to which the "a" channel of the rotary encoder is connected
        pin_b: The pin to which the "b" channel of the rotary encoder is connected

    """

    _states = ['increasing', 'decreasing']

    def __init__(self, name, pin_a: int, pin_b: int):

        # TODO support active-high setups 
        self.a = Pin(pin_a, Pin.IN, Pin.PULL_UP)
        self.b = Pin(pin_b, Pin.IN, Pin.PULL_UP)

        self.a.irq(self.process, Pin.IRQ_FALLING)
        self.b.irq(self.process, Pin.IRQ_FALLING)

        super().__init__(name, api)
        self._state = ''

        # This is a 2-bit value mapped liked so `ab`
        self._last_status = 0

        self._events = {}


    def process(self, _):
        """Poll both switches, recording and evaluating state.

        This method is meant to be used as an interrupt handler for 

        """
        status = self.a.value() << 1 | self.b.value()

        if status == self._last_status:
            return

        transition = self._last_status << 2 | status

        state = None
        # 0b0111, 0b1000: b before a -> decreasing
        if transition == 0b1000:
            state = self._states[1]
        # 0b1011, 0b0100: a before b -> increasing
        elif transition == 0b0100:
            state = self._states[0]

        if state is not None:
            self._state = state
            logger.debug(f"{self.name} state changed to {self.state}")

        self._last_status = status


    async def _loop(self, events):
        self._events = events
