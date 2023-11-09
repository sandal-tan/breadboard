# Pico Enclosure

A micropython framework for interfacing to and managing connected GPIO devices. Provides an API to interact with
connected devices, as well as an event system to trigger actions on system state changes.

Currently supported devices:

- NeoPixel Strips
- 4-pin PWM fans
- CCS811 Gas sensors
- DHT22/AM2302/DHT11 Temperature and humidity sensors
- HD44780U/KS006U-based LCD's
- Toggle buttons
- Momentary Buttons

## Configuration

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
  }
}
```

Devices are added to a map, with a device name as key. The added value is itself a map that should contain a device
designation (the `"device"` key used above) and any other instantiation parameters required to configure the device.

### Networking

If using a Pico W or Pico WH, you can configure the network via a network entry in `devices.json`:

```json
{
  "exhaust_fan": {},
  "lights": {},
  "network": {
    "ssid": "<your_ssid>",
    "password": "<your_password>"
  }
}
```

If no network is configured, an Ad-Hoc network will be created.

## API

An API is provided to interface with the various sensors and devices configured. A list of available endpoints can be
found at `http://<your_pico>:8080/docs`. Devices can be accessed via API by their key names like so:

```bash
# Set fan speed to 50%
curl "http://<your_pico>:8080/exhuast_fan/set?value=50"

# Set the LEDs to white
curl "http://<your_pico>:8080/lights/set?red=255&green=255&brightness=10
```

## Chains

Device actions can be grouped as a set of ordered-steps called chains:

```json
{
  "exhaust_fan": {},
  "lights": {},
  "chains": {
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

Chains are also made available via API:

```bash
# Trigger the `start_print` chain
curl "http://<your_pico>:8080/chains/start_print
```

## Events

Events are when a `StatefulDevice` has a state change. Event Actions (different from the Actions above) are the actions
taken when a state is changed to a specific value. The following event action types are supported:

- Webhook: Make a GET request to a provided URL
- Device: execute a device function

Multiple event actions can be defined for a single state change. Here is an example of event action configurations:

```json
{
  "home_button": {
    "device": "MomentaryButton",
    "pin": 5,
    "mode": "momentary"
  },
  "fluidnc": {
    "device": "Serial",
    "uart_id": 0
  },
  "display": {
    "device": "HD44780U_LCD",
    "register_shift_pin": 16,
    "enable_pin": 17,
    "data_pins": [21, 20, 19, 18]
  },
  "events": [
    {
      "device": "home_button",
      "state": "on",
      "action": [
        {
          "device": {
            "name": "fluidnc",
            "action": "write",
            "data": "$H"
          }
        },
        "device": "display",
        "action": "write",
        "string": "Homing..."
      ]
    }
  ]
}
```
