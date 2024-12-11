"""Aggregate and manage attached devices via a configuration file."""
import asyncio
import json

from micropython import const  # pyright: ignore [reportMissingImports]

from .api import FileResult, HTTP_METHODS, MultiPartUpload, api
from .button import MomentaryButton, ToggleButton, VirtualToggleButton
from .environment import CCS811, DHT11, DHT22
from .event_actions import parse_event_actions
from .fan import Fan
from .lcd import HD44780U_LCD
from .led import NeoPixel, OnboardLED, RGBNeoPixel
from .matrix import Matrix
from .network import Network
from .rotary_encoder import RotaryEncoder
from .serial import Serial
from .switch import Switch
from .ir import IRReceiver

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
    const("RotaryEncoder"): RotaryEncoder.try_to_instantiate(),
    const("IRReceiver"): IRReceiver.try_to_instantiate(),
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


class Devices:
    """Manage attached devices.

    Args:
        path: The path the configuration file

    Attributes:
        devices: The discovered devices

    """

    def __init__(self, path: str = DEFAULT_CONFIG_FILE):
        self._config_path = path
        with open(self._config_path, "r") as fp:
            device_json = json.load(fp)


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

        api.route("/config")(self.read_config)
        api.route("/config", method=HTTP_METHODS.POST)(self.write_config)

        if network_json := device_json.get(NETWORK_CONFIG_KEY):
            self._network = Network(**network_json)
        else:
            self._network = None

    async def read_config(self):
        """Read the system configuration."""
        return FileResult(path=self._config_path)

    async def write_config(self, config: MultiPartUpload):
        """Write a configuration."""
        return {}

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
