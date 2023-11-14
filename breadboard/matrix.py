import asyncio
from machine import Pin, Signal  # pyright: ignore [reportMissingImports]

from .api import api
from .base import StatefulDevice
from .logging import logger


class Matrix(StatefulDevice):
    """A button matrix.

    Args:
        name: A name for the matrix
        row_pins: The pins that are attached to the rows
        column_pins: The pins that are attached to the columns
        poll_sleep: The amount of time to sleep between polling buttons
        button_debounce: How long to sleep after a state change is detected

    """

    def __init__(
        self, name, row_pins, column_pins, poll_sleep=0.05, button_debounce=0.125
    ):
        super().__init__(name, api)

        self.rows = [
            Signal(Pin(pin_number, Pin.IN, pull=Pin.PULL_DOWN))
            for pin_number in row_pins
        ]
        self.columns = [Signal(Pin(pin_number, Pin.OUT)) for pin_number in column_pins]
        self._state = "None"
        self.poll_sleep = poll_sleep
        self.button_debounce = button_debounce

    async def manage_state(self):
        state = None
        for column_idx, column in enumerate(self.columns):
            column.on()
            for row_idx, row in enumerate(self.rows):
                if row.value():
                    state = f"{column_idx}_{row_idx}"
                    break
            column.off()
            if state is not None:
                break
        else:
            state = "None"

        if state is not None and state != self._state:
            self._state = state
            logger.debug(f"{self.name} state changed to {self.state}")
            await asyncio.sleep(self.button_debounce)

    async def _loop(self, events):
        while True:
            await self.process_events(events)
            await asyncio.sleep(self.poll_sleep)
