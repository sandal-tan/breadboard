"""Aggregate and manage attached devices via a configuration file.

```json
{
    "exhaust_fan": {
        "device": "Fan",
        "pin": 17
    },
    "lights": {
        "device": "LEDStrip",
        "pin":  27,
        "led_count": 12
    },
    "network": {
        "ssid": "xxyyzz",
        "password": "asdf1234"
    }
}
```

"""
import json

from micropython import const  # pyright: ignore

from .fan import Fan
from .led_strip import LEDStrip
from .network import Network
from .environment import CCS811, DHT11, DHT22

DEVICE_MAP = {
    const("Fan"): Fan,
    const("LEDStrip"): LEDStrip,
    const("CCS811"): CCS811,
    const("DHT11"): DHT11,
    const("DHT22"): DHT22,
    const("AM2302"): DHT22,
}

DEFAULT_CONFIG_FILE: str = "devices.json"
"""The path to the default configuration file."""


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

    return _inner


class Devices:
    """Manage attached devices.

    Args:
        path: The path the configuration file

    Attributes:
        actions: A collection of user-defined steps of function calls
        devices: The discovered devices

    """

    def __init__(self, path: str = DEFAULT_CONFIG_FILE):
        with open(path, "r") as fp:
            device_json = json.load(fp)

        self._network = Network(**device_json.get("network") or {})
        self.actions = {}

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
                }
            )
            for name, entry in device_json.items()
            if name not in ["network", "actions"]
        }

        for action_name, steps in device_json["actions"].items():
            compiled_steps = []

            for step in steps:
                action_func = getattr(
                    self.devices[step.pop("device")],
                    step.pop("action"),
                )
                compiled_steps.append(_curry(action_func, step))

            self.actions[action_name] = _execute_functions(compiled_steps)

    def __getitem__(self, key):
        return self.devices[key]
