import uasyncio as asyncio
import gc

from breadboard.devices import Devices

gc.enable()
devices = Devices()
try:
    asyncio.run(devices.loop())
finally:
    asyncio.new_event_loop()
