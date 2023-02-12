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

from .fan import Fan
from .led_strip import LEDStrip
from .network import Network

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

        self._network = Network(**device_json.get("network") or {})

        self.devices = {
            name: DEVICE_MAP[entry["device"]](
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
            if name not in ["network"]
        }

    def __getitem__(self, key):
        return self.devices[key]
