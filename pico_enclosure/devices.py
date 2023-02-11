"""Aggregate and manage attached devices via a configuration file.

```json
[
    {
        "device": "Fan",
        "pin": 17
    },
    {
        "device": "LEDStrip",
        "pin":  27,
        "led_count": 12
    }
]

```

"""
import json

from .fan import Fan
from .led_strip import LEDStrip

DEVICE_MAP = {
    "Fan": Fan,
    "LEDStrip": LEDStrip,
}


class Devices:
    """Manage attached devices.

    Args:
        path: The path the configuration file

    """

    def __init__(self, path="devices.json"):
        with open(path, "r") as fp:
            device_json = json.load(fp)

        self.devices = {
            entry["name"]: DEVICE_MAP[entry["device"]](
                **{
                    k: v
                    for k, v in entry.items()
                    if k
                    not in [
                        "device",
                        "name",
                    ]
                }
            )
            for entry in device_json
        }

    def __getitem__(self, key):
        return self.devices[key]
