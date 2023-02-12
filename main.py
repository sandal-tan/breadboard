import uasyncio as asyncio

from pico_enclosure.loop import loop

try:
    asyncio.run(loop())
finally:
    asyncio.new_event_loop()
