"""Button Interface."""

import asyncio

from micropython import const  # pyright: ignore [reportMissingImports]
from machine import Signal, Pin  # pyright: ignore [reportMissingImports]

from .api import api
from .base import StatefulDevice
from .const import DEFAULT_POLLING_SLEEP_TIME, DEFAULT_DEBOUNCE_TIME
from .logging import logger

DEFAULT_PULL_DIRECTION: str = const("down")


class Button(StatefulDevice):
    """Default button logic.

    Args:
        name: A name for the button
        pin: The pin to which the button is connected
        poll_sleep: How long to rest between checking button states
        pull: The pull direction of pin. Down is active high, Up is active low.

    """

    _states = ["off", "on"]

    def __init__(
        self,
        name: str,
        pin: int,
        poll_sleep: float = DEFAULT_POLLING_SLEEP_TIME,
        pull: str = "down",
    ):
        self.input = Signal(Pin(pin, Pin.IN, Pin.PULL_DOWN), invert=(pull == "up"))
        self.poll_sleep = poll_sleep

        super().__init__(name, api)


class ToggleButton(Button):
    """A physical toggle button.


    Args:
        name: A name for the button
        pin: The GPIO pin on which the physical button is an input
        poll_sleep: How long to sleep between polling for the button
        pull: Whether to use a pull up or pull down resistor with the button

    """

    def __init__(
        self,
        name,
        pin,
        poll_sleep: float = DEFAULT_POLLING_SLEEP_TIME,
        pull: str = "down",
    ):
        super().__init__(name, pin, poll_sleep, pull)

        self._state = self.states[1] if self.input.value() else self.states[0]
        self._last_state = None

    async def manage_state(self):
        """Toggle the internal state of the button between on and off."""
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
            await self.process_events(events)
            await asyncio.sleep(self.poll_sleep)


class _ButtonModes:
    toggle = 1
    momentary = 2

    @classmethod
    def __getitem__(cls, key):
        return {"toggle": cls.toggle, "momentary": cls.momentary}[key]


class MomentaryButton(Button):
    """A physical momentary button.

    Args:
        name: A name for the button
        pin: The GPIO pin on which the physical button is an input
        mode: A mode for the button's state management
        poll_sleep: How long to sleep between polling for the button
        button_debounce: How long to sleep after a button state change has been detected
        pull: Whether to use a pull up or pull down resistor with the button

    """

    def __init__(
        self,
        name,
        pin,
        mode=_ButtonModes.momentary,
        poll_sleep=DEFAULT_POLLING_SLEEP_TIME,
        button_debounce=DEFAULT_DEBOUNCE_TIME,
        pull="down",
    ):
        super().__init__(name, pin, poll_sleep, pull)

        self._state = self.states[1] if self.input.value() else self.states[0]
        # At a class level, you can't subscript a type à la `_ButtonModes["toggle"]`
        # so call the underlying method
        self.mode = _ButtonModes.__getitem__(mode)
        if self.mode == _ButtonModes.toggle:
            self.manage_state = self.toggle_state
        elif self.mode == _ButtonModes.momentary:
            self.manage_state = self.momentary_state
        self.button_debounce = button_debounce
        self._last_value = None

    async def momentary_state(self):
        """Register a button press.

        As a momentary button, the on-off state change will happen on every button press.
        Therefore the on-state change will correspond to the rising edge and the off-state
        the falling edge.

        """
        value = self.input.value()
        if value != self._last_value:
            self._last_value = value
            self._state = self.states[value]
            logger.debug(f"{self.name} state changed to {self.state}")
            await asyncio.sleep(self.button_debounce)

    async def toggle_state(self):
        """Make the momentary button act as a a toggle button."""
        if self.input.value():
            if self.state == self.states[0]:
                self._state = self.states[1]
            else:
                self._state = self.states[0]
            await asyncio.sleep(self.button_debounce)
            logger.debug(f"{self.name} state changed to {self.state}")

    async def _loop(self, events):
        while True:
            await self.process_events(events)
            await asyncio.sleep(self.poll_sleep)


class VirtualToggleButton(StatefulDevice):
    """A virtual toggle button, accessible via API.

    Args:
        name: A unique identifier for the button
        pin: The number of the GPIO to use as a signal output

    """

    _states = Button._states

    def __init__(self, name, pin, default_value=None):
        self.output = Pin(pin, Pin.OUT, Pin.PULL_UP)

        super().__init__(name, api)

        if default_value is not None and default_value not in self.states:
            raise RuntimeError(
                f"Default value for {self.name} must be one of: {self.states}"
            )

        self._state = default_value or self.states[0]

        self.group.route("/on")(self.on)
        self.group.route("/off")(self.off)
        self._events = {}  # see comment in _loop

    async def manage_state(self):
        """Togglt the state between on and off on access."""
        if self.state == self.states[0]:
            self._state = self.states[1]
        else:
            self._state = self.states[0]
        logger.debug(f"{self.name} state changed to {self.state}")
        return self.state

    async def _loop(self, events):
        # There isn't a need for a loop when we don't need to poll IO for status changes.
        # This just serves to patch in the events for the API endpoints to be able to trigger
        # events.
        self._events = events

    async def on(self):
        """Turn on the virtual button."""
        self.output.on()
        if self.state == self.states[0]:
            await self.process_events(self._events)
        return {"state": self.state}

    async def off(self):
        """Turn off the virtual button."""
        self.output.off()
        if self.state == self.states[1]:
            await self.process_events(self._events)
        return {"state": self.state}
