"""The main execution loop."""

import uasyncio as asyncio

from .api import api
from .network import Network


async def loop():
    Network()
    asyncio.create_task(asyncio.start_server(api.route_requests, "0.0.0.0", 8080))
    while True:
        await asyncio.sleep(5)
