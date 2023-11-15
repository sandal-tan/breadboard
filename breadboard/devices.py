"""Aggregate and manage attached devices via a configuration file."""
import os
import json

from micropython import const  # pyright: ignore
import asyncio
import gc

from .button import VirtualToggleButton, MomentaryButton, ToggleButton
from .fan import Fan
from .led import NeoPixel, OnboardLED, RGBNeoPixel
from .network import Network
from .environment import CCS811, DHT11, DHT22
from .api import api
from .lcd import HD44780U_LCD
from .logging import logger
from .matrix import Matrix
from .event_actions import parse_event_actions
from .rotary_encoder import RotaryEncoder
from .serial import Serial
from .switch import Switch

DEVICE_MAP = {
    const("Fan"): Fan.try_to_instantiate(),
    const("NeoPixel"): NeoPixel.try_to_instantiate(),
    const("RGBNeoPixel"): RGBNeoPixel.try_to_instantiate(),
    const("CCS811"): CCS811.try_to_instantiate(),
    const("DHT11"): DHT11.try_to_instantiate(),
    const("DHT22"): DHT22.try_to_instantiate(),
    const("AM2302"): DHT22.try_to_instantiate(),
    const("VirtualToggleButton"): VirtualToggleButton.try_to_instantiate(),
    const("MomentaryButton"): MomentaryButton.try_to_instantiate(),
    const("ToggleButton"): ToggleButton.try_to_instantiate(),
    const("Serial"): Serial.try_to_instantiate(),
    const("Switch"): Switch.try_to_instantiate(),
    const("HD44780U_LCD"): HD44780U_LCD.try_to_instantiate(),
    const("Matrix"): Matrix.try_to_instantiate(),
    const("RotaryEncoder"): RotaryEncoder.try_to_instantiate()
}

DEFAULT_CONFIG_FILE: str = const("breadboard.json")
"""The path to the default configuration file."""

NETWORK_CONFIG_KEY: str = const("network")
"""The key for the network configuration section."""

CHAINS_CONFIG_KEY: str = const("chains")
"""The key for the chains configuration section."""

CONTEXT_CONFIG_KEY: str = const("context")
"""The key for the context configuration section."""

EVENTS_CONTEXT_KEY: str = const("events")
"""The key for the events configuration section."""


def _curry(func, params):
    """Bake a set of parameters to a asynchronous function call as a function."""

    async def _inner():
        return await func(**params)

    return _inner


def _execute_functions(functions):
    """Construct an asynchronous function to execute a list of asynchronous functions."""

    async def _inner():
        for function in functions:
            await function()
        return {}

    return _inner


class Devices:
    """Manage attached devices.

    Args:
        path: The path the configuration file

    Attributes:
        devices: The discovered devices

    """

    def __init__(self, path: str = DEFAULT_CONFIG_FILE):
        with open(path, "r") as fp:
            device_json = json.load(fp)

        if network_json := device_json.get(NETWORK_CONFIG_KEY):
            self._network = Network(**network_json)
        else:
            self._network = None

        self.devices = {
            name: DEVICE_MAP[entry["device"]](
                name=name,
                **{
                    k: v
                    for k, v in entry.items()
                    if k
                    not in [
                        "device",
                    ]
                },
            )
            for name, entry in device_json.items()
            if name
            not in [
                NETWORK_CONFIG_KEY,
                CHAINS_CONFIG_KEY,
                CONTEXT_CONFIG_KEY,
                EVENTS_CONTEXT_KEY,
            ]
        }

        self.devices = {k: v for k, v in self.devices.items() if v}
        self.devices["_OnboardLED"] = OnboardLED()

        for chain_name, steps in device_json.get(CHAINS_CONFIG_KEY, {}).items():
            compiled_steps = []

            for step in steps:
                try:
                    # TODO should these share the same underlying actions as events?
                    chain_func = getattr(
                        self.devices[step.pop("device")],
                        step.pop("action"),
                    )
                    compiled_steps.append(_curry(chain_func, step))
                except KeyError as e:
                    logger.error(
                        "Failed to find device %s for action %s", str(e), chain_name
                    )
                    break
                except Exception as e:
                    logger.error("Failed to load action: %s", chain_name)
                    logger.error(str(e))
                    break
            else:
                if self._network:
                    api.route(f"/chain/{chain_name}")(
                        _execute_functions(compiled_steps)
                    )

        self.events = {}
        for event in device_json.get(EVENTS_CONTEXT_KEY, []):
            device = event.pop("device")
            if device not in self.events:
                self.events[device] = {}
            state = event.pop("state")
            if state not in self.events[device]:
                self.events[device][state] = []
            self.events[device][state].extend(
                parse_event_actions(event.pop("action"), devices=self.devices)
            )

        gc.collect()

        if self._network:
            api.documentation  # Generate the documentation

    def __getitem__(self, key):
        return self.devices[key]

    async def loop(self):
        """The main execution loop."""

        if self._network:
            asyncio.create_task(
                asyncio.start_server(
                    api.route_requests,
                    self._network.hosts,
                    self._network.port,
                )
            )

        for device in self.devices.values():
            if device is not None:
                asyncio.create_task(device._loop(events=self.events))

        while True:
            await asyncio.sleep(5)
