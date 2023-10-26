"""Button Interface."""

import uasyncio as asyncio  # pyright: ignore [reportMissingImports]

from machine import Pin  # pyright: ignore [reportMissingImports]

from .base import BaseDevice, StatefulDevice
from .api import api
from .logging import logger


class _ButtonModes:
    toggle = 1

    @classmethod
    def __getitem__(cls, key):
        return {"toggle": cls.toggle}[key]


ButtonModes = _ButtonModes()


class ToggleButton(StatefulDevice):
    __doc__ = """A physical toggle button.


    Args:
        name: A name for the button
        pin: The GPIO pin on which the physical button is an input
        poll_sleep: How long to sleep between polling for the button
        button_debounce: How long to sleep after a button state change has been detected

    """

    _states = ["off", "on"]

    def __init__(self, name, pin, poll_sleep=0.1):
        self.input = Pin(pin, Pin.IN, Pin.PULL_DOWN)
        super().__init__(name, api)

        self._state = self.states[1] if self.input.value() else self.states[0]
        self.on_state_change = self.toggle_state
        self.poll_sleep = poll_sleep
        self._last_state = None

    def toggle_state(self):
        if (value := self.input.value()) != self._last_state:
            if value:
                self._state = self.states[1]
            else:
                self._state = self.states[0]
            logger.debug(f"{self.name} state changed to {self.state}")
            self._last_state = value
        return self.state

    async def _loop(self, events):
        while True:
            await self.manage_state(events)
            await asyncio.sleep(self.poll_sleep)


class MomentaryButton(StatefulDevice):
    __doc__ = """A physical momentary button.

    Args:
        name: A name for the button
        pin: The GPIO pin on which the physical button is an input
        mode: A mode for the button's state management
        poll_sleep: How long to sleep between polling for the button
        button_debounce: How long to sleep after a button state change has been detected

    """

    _states = ["off", "on"]

    def __init__(self, name, pin, mode, poll_sleep=0.1, button_debounce=0.5):
        self.input = Pin(pin, Pin.IN, Pin.PULL_DOWN)
        super().__init__(name, api)

        self._state = self.states[1] if self.input.value() else self.states[0]
        self.mode = ButtonModes[mode]
        if self.mode == ButtonModes.toggle:
            self.on_state_change = self.toggle_state
        self.poll_sleep = poll_sleep
        self.button_debounce = button_debounce

    def toggle_state(self):
        if self.state == self.states[0]:
            self._state = self.states[1]
        else:
            self._state = self.states[0]
        logger.debug(f"{self.name} state changed to {self.state}")
        return self.state

    async def _loop(self, events):
        while True:
            if self.input.value():
                await self.manage_state(events)
                await asyncio.sleep(self.button_debounce)
            await asyncio.sleep(self.poll_sleep)


class VirtualToggleButton(StatefulDevice):
    __doc__ = """A virtual toggle button, accessible via API.

    Args:
        name: A unique identifier for the button
        pin: The number of the GPIO to use as a signal output

    """
    _states = ["off", "on"]

    def __init__(self, name, pin, default_value=None):
        self.output = Pin(pin, Pin.OUT, Pin.PULL_UP)

        super().__init__(name, api)

        if default_value is not None and default_value not in self.states:
            raise RuntimeError(
                f"Default value for {self.name} must be one of: {self.states}"
            )

        self._state = default_value if default_value is not None else self.states[0]
        self.on_state_change = self.toggle_state

        self.group.route("/on")(self.on)
        self.group.route("/off")(self.off)
        self._events = None

    def toggle_state(self):
        if self.state == self.states[0]:
            self._state = self.states[1]
        else:
            self._state = self.states[0]
        logger.debug(f"{self.name} state changed to {self.state}")
        return self.state

    async def _loop(self, events):
        """There isn't a need for a loop when we don't need to poll IO for status changes.
        This just serves to patch in the events for the API endpoints to be able to trigger
        events.
        """
        self._events = events
        await self.manage_state(self._events)

    @api.doc("""Turn on the virtual button.""")
    async def on(self):
        self.output.on()
        if self.state == self.states[0]:
            await self.manage_state(self._events)
        return {"state": self.state}

    @api.doc("""Turn off the virtual button.""")
    async def off(self):
        self.output.off()
        if self.state == self.states[1]:
            await self.manage_state(self._events)
        return {"state": self.state}
