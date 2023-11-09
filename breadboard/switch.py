"""Interface with switches as selectors."""

import asyncio
from machine import Pin  # pyright: ignore [reportMissingImports]
from micropython import const  # pyright: ignore[reportMissingImports]

from .api import api
from .base import StatefulDevice
from .logging import logger

OFF_STATE: str = const("off")
"""The constat to represent the off state of a switch."""


class Switch(StatefulDevice):
    ___doc__ = """A physical switch with multiple state options.

    Args:
        name: A name for the switch
         state_pin_mapping: Map desired states to GPIO pins and OFF
         poll_sleep: How long to rest between state checks

    """

    def __init__(self, name, state_pin_mapping, poll_sleep=0.1):
        super().__init__(name, api)
        self._states = []
        self._pins_to_state = {}
        self._state = None
        for state, pin in state_pin_mapping.items():
            self._states.append(state)
            if pin is not OFF_STATE:
                input_pin = Pin(pin, Pin.IN, Pin.PULL_DOWN)
                if input_pin.value():
                    if self._state is not None:
                        raise RuntimeError(f"Multiple states set on: {self.name}")
                    self._state = state
                self._pins_to_state[pin] = (input_pin, state)
            else:
                self._pins_to_state[OFF_STATE] = (None, state)

        if self._state is None:
            self._state = self._pins_to_state[OFF_STATE][1]

        self.poll_sleep = poll_sleep

    def manage_state(self):
        """Toggle between states based on the pin's physical state."""
        pin_active = False
        for pin, state in self._pins_to_state.values():
            if pin and pin.value():
                pin_active = True
                if state != self._state:
                    self._state = state
                    logger.debug(f"{self.name} state changed to {self.state}")
                    return
        else:
            if not pin_active and self._state != self._pins_to_state[OFF_STATE][1]:
                self._state = self._pins_to_state[OFF_STATE][1]
                logger.debug(f"{self.name} state changed to {self.state}")

    async def _loop(self, events):
        while True:
            await self.process_events(events)
            await asyncio.sleep(self.poll_sleep)
