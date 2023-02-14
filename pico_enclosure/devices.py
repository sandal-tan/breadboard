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

from micropython import const

from .air_quality import CCS811AirQualitySesnor
from .fan import Fan
from .led_strip import LEDStrip
from .network import Network

DEVICE_MAP = {
    const("Fan"): Fan,
    const("LEDStrip"): LEDStrip,
    const("CCS811"): CCS811AirQualitySesnor,
}


def _curry(func, params):
    async def _inner():
        return await func(**params)

    return _inner


def _execute_functions(functions):
    async def _inner():
        for function in functions:
            await function()

    return _inner


class Devices:
    """Manage attached devices.

    Args:
        path: The path the configuration file

    """

    def __init__(self, path="devices.json"):
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
