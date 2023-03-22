import uasyncio as asyncio
import gc

from pico_enclosure.devices import Devices

gc.enable()
devices = Devices()
try:
    asyncio.run(devices.loop())
finally:
    asyncio.new_event_loop()
