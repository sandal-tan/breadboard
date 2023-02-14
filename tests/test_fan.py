from time import sleep
import uasyncio as asyncio

from machine import Pin
from pico_enclosure.devices import Devices

led = Pin("LED", Pin.IN)
led.value(1)
try:
    devices = Devices()
    fan = devices["exhaust_fan"]

    for speed in range(0, 105, 5):
        asyncio.run(fan.set(speed))
        sleep(2)

    asyncio.run(fan.set(50))
    sleep(2)
    asyncio.run(fan.off())
    sleep(10)
    asyncio.run(fan.on())

finally:
    led.value(0)
