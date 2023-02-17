import uasyncio as asyncio

from pico_enclosure.devices import Devices

devices = Devices()
try:
    asyncio.run(devices.loop())
finally:
    asyncio.new_event_loop()
