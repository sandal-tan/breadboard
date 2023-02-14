"""The main execution loop."""

from machine import Pin

import uasyncio as asyncio

from .network import Network
from .devices import Devices
from .api import api


async def loop():
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
