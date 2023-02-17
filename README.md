# Pico Enclosure

A Raspberry Pico based framework for building "smart" enclosures and providing an API interfacing with attached sensors and devices.

Currently supported devices:

- NeoPixel Strips
- 4-pin PWM fans
- CCS811 Gas sensors
- DHT22/AM2302/DHT11 Temperature and humidity sensors

Devices are configured with a `devices.json` file that is installed onto the Pico:

```json
{
  "exhaust_fan": {
    "device": "Fan",
    "pin": 17
  },
  "lights": {
    "device": "NeoPixelStrip",
    "pin": 27,
    "led_count": 170
  },
  ...
}
```

Devices are added to a map, with a device name as key. The added value is itself a map
that should contain a device designation (the `"device"` key used above) and any other
instantiation parameters required to configure the device.

If using a Pico W or Pico WH, you can configure the network via a network entry in `devices.json`:

```json
{
    "exhaust_fan": {...},
    "lights": {...},
    "network": {
        "ssid": "<your_ssid>",
        "password": "<your_password>"
    }

}
```

If no network is configured, an Ad-Hoc network will be created.

An API is provided to interface with the various sensors and devices configured. A list of available
endpoints can be found at `http://<your_pico>:8080/docs`. Generally speaking, devices can be accessed
via API by their key names like so:

```bash
# Set fan speed to 50%
curl "http://<your_pico>:8080/exhuast_fan/set?value=50"

# Set the LEDs to white
curl "http://<your_pico>:8080/lights/set?red=255&green=255&brightness=10
```

Device endpoints can be grouped as a set of ordered-steps called actions:

```json
{
    "exhaust_fan": {...},
    "lights": {...},
    "actions": {
        "start_print": [
            {
                "device": "lights",
                "action": "set",
                "red": 255,
                "green": 255,
                "blue": 100,
                "brightness": 75
            },
            {
                "device": "exhaust_fan",
                "action": "set",
                "value": 50
            }
        ]
    }
}

```

Actions are also made available via API:

```bash
# Trigger the `start_print` action
curl "http://<your_pico>:8080/actions/start_print
```
