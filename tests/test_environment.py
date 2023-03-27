import uasyncio as asyncio
from time import sleep


from machine import Pin

from breadboard.devices import Devices

led = Pin("LED", Pin.IN)
led.value(1)
try:
    devices = Devices()

    sensor = devices["interior_air"]
    print(asyncio.run(sensor.status()))

    sensor = devices["interior_temp"]
    print(asyncio.run(sensor.data()))

finally:
    led.value(0)
