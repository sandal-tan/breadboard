"""The main execution loop."""

from machine import Pin  # pyright: ignore[reportMissingImports]

import uasyncio as asyncio  # pyright: ignore[reportMissingImports]

from .devices import Devices
from .api import api


async def loop():
    """The main execution loop."""
    devices = Devices()

    for action, action_func in devices.actions.items():
        api.route(f"/action/{action}")(action_func)

    led = Pin("LED", Pin.OUT)
    led.value(1)
    try:
        asyncio.create_task(asyncio.start_server(api.route_requests, "0.0.0.0", 8080))
        while True:
            await asyncio.sleep(5)
    finally:
        led.value(0)
