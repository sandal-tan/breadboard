"""Interface with a CCS811 Air Quailty Sensor"""

from time import sleep_ms

from machine import SoftI2C, Pin
from micropython import const
import uasyncio as asyncio

from .api import api

HARDWAREESSES = (
    0x5A,
    0x5B,
)  # https://cdn-shop.adafruit.com/product-files/3566/3566_datasheet.pdf#page=4&zoom=100,96,177

DELAY: int = 100

# Registers
# TODO: source
STATUS_REG = (const(0x00), const(1))  # R   - 1 Byte  - Status
MEAS_REG = (const(0x01), const(1))  #   R/W - 1 Byte  - Measurement mode and conditions
ALG_REG = (const(0x02), const(8))  #    R   - 8 bytes - Algorithm Results
RAW_REG = (const(0x03), const(2))  #    R   - 2 bytes - Raw ADC values
ENV_REG = (const(0x04), const(4))  #    W   - 4 bytes - Temperature and humdity values
NTC_REG = (
    const(0x06),
    const(4),
)  #    R   - 4 bytes - Voltage across reference resistor
THRES_REG = (const(0x10), const(5))  #  W   - 5 bytes - eCO2 ppm operation thresholds
BASE_REG = (const(0x11), const(2))  #   R/W - 2 bytes - Encoded baseline values
HW_ID_REG = (const(0x20), const(1))  #  R   - 1 byte  - Hardware ID. Expected 0x81
HW_VER_REG = (
    const(0x21),
    const(1),
)  # R   - 1 byte  - The hardware version. Expected 0x1XK
BOOT_F_REG = (const(0x23), const(1))  # R   - 2 bytes - Firmware boot version
APP_F_REG = (const(0x24), const(2))  #  R   - 2 bytes - Firmware application version
ERROR_REG = (const(0xE0), const(1))  #  R   - 1 byte  - Error id
APP_START_REG = (const(0xF4), None)
SW_RST_REG = (
    const(0xFF),
    const(4),
)  # W   - 4 bytes - Reset pin. Write 0x11 0xE5 0x72 0x8A


int_from_bytes = lambda v: int.from_bytes(v, "big")


class CCS811AirQualitySesnor:
    """I2C Sensor for measuring VOCs and eCO2.

    Args:
        name: A unique name for the sensor
        sda: The SDA pin to which the sensor is connected
        scl: The SCL pin to which the sensor is connected
        mode: The starting mode of operation
        interrupt_pin: The GPIO Pin to which the interrupt Pin is connected

    """

    def __init__(
        self,
        name: str,
        sda: int,
        scl: int,
        mode: int = 1,
        interrupt_pin=None,
    ):
        self.name = name
        self._default_mode = mode
        self.interrupt_pin = interrupt_pin
        self.i2c_bus = SoftI2C(
            sda=Pin(sda),
            scl=Pin(scl),
            timeout=2000,
        )
        sleep_ms(DELAY)
        for device in self.i2c_bus.scan():
            if device in HARDWAREESSES:
                self.device_addr = device
                print(f"Found device at {hex(device)}")
            break
        else:
            raise Exception("No CCS811 devices could be found")

        self.i2c_bus.writeto_mem(
            self.device_addr,
            SW_RST_REG[0],
            b"\x11\xE5\x72\x8A",
        )
        sleep_ms(DELAY)

        status = asyncio.run(self.status())
        if not status["error"] and status["app_valid"]:
            print(f"Device at {hex(self.device_addr)} ready.")
            self._start()
            asyncio.run(self.mode(self._default_mode))

        api.route(f"/{self.name}/mode")(self.mode)
        api.route(f"/{self.name}/status")(self.status)
        api.route(f"/{self.name}/data")(self.data)
        api.route(f"/{self.name}/error")(self.error)

    def _start(self):
        # https://cdn-shop.adafruit.com/product-files/3566/3566_datasheet.pdf#page=24&zoom=100,96,177
        self.i2c_bus.writeto_mem(
            self.device_addr,
            APP_START_REG[0],
            b"",
        )
        sleep_ms(DELAY)

    async def mode(self, mode: int = None):
        """Set the chip mode.

        Args:
            mode: The mode of operation to put the sensor in

        Returns:
            JSON representing containg the mode keys and values if mode is not given, echos the mode if given

        Notes:
            This implementation does not support threshold based interrupts on the sensor.

        Sources:
            - https://cdn-shop.adafruit.com/product-files/3566/3566_datasheet.pdf#page=16&zoom=100,96,177

        """
        if mode is not None:
            mode = int(mode)
            if mode == 4:
                raise Exception("Mode 4 is not supported")
            byte = 0b0_111_0000 & mode << 4
            # byte &= 1 if self.interrupt_pin else 0 << 3
            self.i2c_bus.writeto_mem(
                self.device_addr,
                MEAS_REG[0],
                byte.to_bytes(1, "big"),
            )
            asyncio.sleep_ms(DELAY)
            return mode
        else:
            mode = int_from_bytes(
                self.i2c_bus.readfrom_mem(
                    self.device_addr,
                    *MEAS_REG,
                ),
            )
            asyncio.sleep_ms(DELAY)
            return {
                "drive_mode": mode >> 4,
                "interrupt_data_ready": bool(mode >> 3 & 1),
            }

    @staticmethod
    def _parse_status(status_byte):
        return {
            "fw_mode": bool(status_byte >> 7 & 1),
            "app_valid": bool(status_byte >> 4 & 1),
            "data_ready": bool(status_byte >> 3 & 1),
            "error": bool(status_byte & 1),
        }

    async def status(self):
        """Read the status of the CCS811.

        Returns:
            JSON containg the status of the sensor

        Sources:
            - https://cdn-shop.adafruit.com/product-files/3566/3566_datasheet.pdf#page=16&zoom=100,96,177

        """
        status_byte = int_from_bytes(
            self.i2c_bus.readfrom_mem(
                self.device_addr,
                *STATUS_REG,
            )
        )
        asyncio.sleep_ms(DELAY)
        return self._parse_status(status_byte)

    async def data(self, status=False, error=False):
        """Get the algorithm results from the sensor.

        Args:
            status: Include the status response byte with the data
            error: Include the error reponse with the data

        Returns:
            JSON contain the sensor measurements.

        Sources:
            - https://cdn-shop.adafruit.com/product-files/3566/3566_datasheet.pdf#page=18&zoom=100,96,177

        """
        data = self.i2c_bus.readfrom_mem(
            self.device_addr,
            *ALG_REG,
        )

        res = {
            "eCO2": int_from_bytes(data[:2]),
            "TVOC": int_from_bytes(data[2:4]),
        }

        if status or status == "true":
            res.update(self._parse_status(data[4]))

        if error or error == "true":
            res.update(self._parse_error(data[5]))

        asyncio.sleep_ms(DELAY)

        return res

    def _parse_error(self, error_byte):
        return {
            "WRITE_REG_INVALID": bool(error_byte & 1),
            "READ_REG_INVALID": bool(error_byte >> 1 & 1),
            "MEASMODE_INVALID": bool(error_byte >> 2 & 1),
            "MAX_RESISTANCE": bool(error_byte >> 3 & 1),
            "HEATER_FAULT": bool(error_byte >> 4 & 1),
            "HEATER_SUPPLY": bool(error_byte >> 5 & 1),
        }

    async def error(self):
        """Get the error state of the sensor.

        Returns:
            JSON contain the various error states

        Sources:
            - https://cdn-shop.adafruit.com/product-files/3566/3566_datasheet.pdf#page=22&zoom=100,96,177

        """
        data = int_from_bytes(
            self.i2c_bus.readfrom_mem(
                self.device_addr,
                *ERROR_REG,
            )
        )
        return self._parse_error(data)
