"""Environment sensors."""

from time import sleep_ms, sleep_us, time  # pyright: ignore

from machine import SoftI2C, Pin  # pyright: ignore
from micropython import const  # pyright: ignore
import uasyncio as asyncio  # pyright: ignore

from .api import api

CCS811_HARDWARE_ADDRS = (
    0x5A,
    0x5B,
)
"""The possible hardware address of the CCS811 sensor.

Sources:
    - https://cdn-shop.adafruit.com/product-files/3566/3566_datasheet.pdf#page=4&zoom=100,96,177
"""

CCS811_DELAY: int = 100

# Registers
# Sources:
# - https://cdn-shop.adafruit.com/product-files/3566/3566_datasheet.pdf#page=15&zoom=100,96,177
# - https://cdn-shop.adafruit.com/product-files/3566/3566_datasheet.pdf#page=24&zoom=100,96,177
CCS811_STATUS_REG = (const(0x00), const(1))
"""Read only 1 byte register for sensor status."""
CCS811_MEAS_REG = (const(0x01), const(1))
"""Read/Write 1 byte register for sensor mode of operation"""
CCS811_ALG_REG = (const(0x02), const(8))
"""Read only 8 byte register containing algorithm results."""
CCS811_ENV_REG = (const(0x04), const(4))
"""Write only 4 byte register for storing temperature and humidity data for compensation."""
CCS811_ERROR_REG = (const(0xE0), const(1))
"""Read only 1 byte register containing the various error codes."""
CCS811_APP_START_REG = (const(0xF4), None)
"""Write only register to info the sensor to begin collecting data."""
CCS811_SW_RST_REG = (const(0xFF), const(4))
"""Software reset pin, puts the sensor into idle."""

DHTXX_EXPECTED_BITS = 40  # 2 bytes each temperature and humidity, 1 byte checksum


int_from_big_bytes = lambda v: int.from_bytes(v, "big")
"""Convert a bytearray into an integer."""


class CCS811:
    """I2C Gas Sensor for measuring VOCs and eCO2.

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
        sleep_ms(CCS811_DELAY)
        for device in self.i2c_bus.scan():
            if device in CCS811_HARDWARE_ADDRS:
                self.device_addr = device
                print(f"Found device at {hex(device)}")
            break
        else:
            raise Exception("No CCS811 devices could be found")

        self.i2c_bus.writeto_mem(
            self.device_addr,
            CCS811_SW_RST_REG[0],
            b"\x11\xE5\x72\x8A",
        )
        sleep_ms(CCS811_DELAY)

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
            CCS811_APP_START_REG[0],
            b"",
        )
        sleep_ms(CCS811_DELAY)

    async def mode(self, mode=None):
        """Set the chip mode.

        Args:
            mode: The mode of operation to put the sensor in

        Returns:
            JSON representation containing the mode keys and values if mode is not given, echos the mode if given

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
                CCS811_MEAS_REG[0],
                byte.to_bytes(1, "big"),
            )
            asyncio.sleep_ms(CCS811_DELAY)
            return mode
        else:
            mode = int_from_big_bytes(
                self.i2c_bus.readfrom_mem(
                    self.device_addr,
                    *CCS811_MEAS_REG,
                ),
            )
            asyncio.sleep_ms(CCS811_DELAY)
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
            JSON containing the status of the sensor

        Sources:
            - https://cdn-shop.adafruit.com/product-files/3566/3566_datasheet.pdf#page=16&zoom=100,96,177

        """
        status_byte = int_from_big_bytes(
            self.i2c_bus.readfrom_mem(
                self.device_addr,
                *CCS811_STATUS_REG,
            )
        )
        asyncio.sleep_ms(CCS811_DELAY)
        return self._parse_status(status_byte)

    async def data(self, status=False, error=False):
        """Get the algorithm results from the sensor.

        Args:
            status: Include the status response byte with the data
            error: Include the error response with the data

        Returns:
            JSON contain the sensor measurements.

        Sources:
            - https://cdn-shop.adafruit.com/product-files/3566/3566_datasheet.pdf#page=18&zoom=100,96,177

        """
        data = self.i2c_bus.readfrom_mem(
            self.device_addr,
            *CCS811_ALG_REG,
        )

        res = {
            "eCO2": int_from_big_bytes(data[:2]),
            "TVOC": int_from_big_bytes(data[2:4]),
        }

        if status or status == "true":
            res.update(self._parse_status(data[4]))

        if error or error == "true":
            res.update(self._parse_error(data[5]))

        asyncio.sleep_ms(CCS811_DELAY)

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
        data = int_from_big_bytes(
            self.i2c_bus.readfrom_mem(
                self.device_addr,
                *CCS811_ERROR_REG,
            )
        )
        return self._parse_error(data)


class DHTXX:
    """Temperature and humidity sensor."""

    def __init__(self, name, pin, rest_time: int) -> None:
        self.name = name
        self.pin = Pin(pin)
        self._last_measurement_time = 0
        self._rest_time = rest_time
        self._temp = None
        self._humidity = None

    async def measure(self):
        """Use the sensor to take a measurement if one is available.

        A new measurement will only be allowed every ``self._rest_time`` seconds.

        Returns:
            JSON containing the temperature and humidity readings.

        """
        current_time = time()
        if current_time - self._last_measurement_time > self._rest_time:
            # Send the start code
            # Pull the pin low for 1ms
            self.pin.value(0)
            sleep_ms(1)
            # Pull the pin high for 20-40us
            self.pin.value(1)
            sleep_us(30)
            # Sensor pulls low for 80us
            while self.pin.value() == 0:
                sleep_us(40)
            # Sensor pulls high for 80us
            while self.pin.value() == 1:
                sleep_us(40)

            # Read Data
            # Wait for the line to be pulled high and then wait
            # longer than the duration of the 0-bit pulse, but
            # not longer than the 1-bit pulse. Get the line value
            # as the bit value, pack it in, and wait to read the next bit.
            bits = 0
            for idx in range(DHTXX_EXPECTED_BITS):
                # Wait for the pin to go high
                while self.pin.value() != 1:
                    sleep_us(25)

                sleep_us(35)

                bits = bits | self.pin.value() << idx
                while self.pin.value() == 1:
                    sleep_us(35)

            self._humidity = bits >> 24  # Get the first 2 bytes
            raw_temp = bits >> 8 & 65535  # Get the middle byte
            # First bit is sign, remaining 15 are temperature
            self._temp = 1 if raw_temp >> 15 else -1 * raw_temp & (2**15 - 1)

            checksum = bits & 255  # Get the last byte

            # Checksum should be the sum of each byte in the temperature and humidity values
            if checksum != (
                (self._humidity >> 8)
                + (self._humidity & 255)
                + (raw_temp >> 8)
                + (raw_temp & 255)
            ):
                raise Exception("Checksum validation failed.")

        return {
            "temperature": self._temp,
            "humidity": self._humidity,
        }


class DHT11(DHTXX):
    """A smaller, cheaper, higher sampling and less accurate temperature and humidity sensor."""

    def __init__(self, name, pin):
        super().__init__(name, pin, 1)


class DHT22(DHTXX):
    """A larger, more expensive, slow sampling and more accurate temperature and humidity sensor."""

    def __init__(self, name, pin):
        super().__init__(name, pin, 2)


AM2302 = DHT22
"""A larger, more expensive, slow sampling and more accurate temperature and humidity sensor."""
