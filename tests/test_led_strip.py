from time import sleep

from machine import Pin
from pico_enclosure.devices import Devices

led = Pin("LED", Pin.IN)
led.value(1)
try:
    devices = Devices()
    strip = devices["lights"]

    for var in [
        (255, 0, 0),  # red
        (0, 255, 0),  # green
        (0, 0, 255),  # blue
    ]:
        strip.fill(*var)
        sleep(2)

    for gradient in [
        ((255, 0, 0), (0, 255, 0)),  # Red to Green
        ((0, 255, 0), (255, 0, 255)),  # Green to Purple
    ]:
        strip.gradient(*gradient)
        sleep(2)

    strip.fill(255, 255, 255, 0.1)
    sleep(2)
    strip.off()
    sleep(2)
    strip.on()
finally:
    led.value(0)
