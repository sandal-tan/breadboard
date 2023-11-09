# Breadboard

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

## Usage & Installation

Breadboard can be deployed and configured as is for simple use cases. To do so, clone the repository:

```bash
$ https://github.com/sandal-tan/breadboard.git
```

Once cloned, Poetry can be used to setup the environment for this project by running

```bash
$ poetry install
```

Alternatively, you can install the environment via pip:

```bash
$ pip install .
```

Once your device is [configured][2] with a `device.json`, you can install the firmware and configuration onto your
device with:

```bash
$ make install
```

Which will compile the bytecode, copy it to the connected device, install the configuration, and start the firmware.

If you wish to tail the execution, you can run:

```bash
$ make debug
```

### Usage in other projects

This package is compatible with [mip][3], to install:

```bash
$ poetry run mpremote mip install github:sandal-tan/breadboard
```

If you wish to include the source in a project for development/whatever needs, this can be done with:

```bash
$ micropython -m mip install github:sandal-tan/breadboard -t . --no-mpy
```

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

## Development Notes

### Micropython

You can install the Unix port of [micropython](https://micropython.org/) on mac using [HomeBrew](https://brew.sh/):

```shell
$ brew install micropython
```

### mpy-cross

[mpy-cross](https://gitlab.com/alelec/mpy_cross) is used to compile the source into bytecode. It is installed as part of
the micropython unix port, but may not be up to date with the latest release of micropython. If that is the case, the
releases can be found [here](https://gitlab.com/alelec/mpy_cross/-/pipelines).
