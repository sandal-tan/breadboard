"""Interact with LCDs."""

import uasyncio as asyncio  # pyright: ignore [reportMissingImports]
from utime import sleep_us  # pyright: ignore [reportMissingImports]

from micropython import const  # pyright: ignore [reportMissingImports]
from machine import Pin  # pyright: ignore [reportMissingImports]

from .api import api
from .base import BaseDevice
from .logging import logger

HD44780U_LCD_CLEAR_SLEEP_TIME: int = const(1600)
"""The number of microseconds to wait after clearing the display."""


class HD44780U_LCD(BaseDevice):
    """An HD44780U-based LCD.

    Args:
        register_select_pin: The GPI pin to which the register select (RS) is connected
        enable_pin: The GPI pin to LCD's enable pin is connected
        data_pins: The pins to which the data lines. To work properly, the pins must be in
            order of their data line (DB0-DB7 or DB4-DB7)).
        columns: The number of columns on the display
        rows: The number of rows on the display
        show_cursor: Whether or not to illuminate the cursor on the display
        blink_cursor: Whether or not the cursor should blink
        default_string: A string to display after initializing the display

    Notes:
        - https://cdn-shop.adafruit.com/datasheets/HD44780.pdf
        - https://www.sparkfun.com/datasheets/LCD/HD44780.pdf
        - https://www.sparkfun.com/datasheets/LCD/GDM1602K-Extended.pdf
        - https://www.circuitschools.com/interfacing-16x2-lcd-module-with-raspberry-pi-pico-with-and-without-i2c/
        - https://www.lcd-module.de/eng/pdf/zubehoer/ks0066.pdf

    """

    UNKNOWN_MODE = 0
    FOUR_BIT_MODE = 1
    EIGHT_BIT_MODE = 2

    def __init__(
        self,
        name,
        register_shift_pin: int,
        enable_pin: int,
        data_pins: list[int],
        columns: int = 16,
        rows: int = 2,
        show_cursor: bool = True,
        blink_cursor: bool = False,
        default_string: str = None,
    ):
        self._rs = Pin(register_shift_pin, Pin.OUT, value=0)
        self._e = Pin(enable_pin, Pin.OUT, value=0)

        self._mode = HD44780U_LCD.UNKNOWN_MODE
        self.columns = columns
        self.rows = rows

        self.show_cursor = show_cursor
        self.blink_cursor = blink_cursor

        if len(data_pins) == 4:
            self._mode = HD44780U_LCD.FOUR_BIT_MODE
            self._set_data = self._set_data_4_bit_mode
        else:
            raise RuntimeError("Only 4-bit mode is supported.")

        self._data_pins = []
        for pin in data_pins:
            p = Pin(pin, Pin.OUT, value=0)
            self._data_pins.append(p)

        super().__init__(name, api)

        self.x = 0
        self.y = 0

        self.group.route("/clear")(self.clear)
        self.group.route("/write")(self.write)
        self._default_string = default_string

    def _enable(self):
        """Start the read/write cycle."""
        self._e.value(0)
        sleep_us(1)
        self._e.value(1)
        sleep_us(1)
        self._e.value(0)
        sleep_us(50)

    def move_to(self, x: int, y: int, update_cursor: bool = True):
        if update_cursor:
            if x > self.columns - 1 or y > self.rows - 1:
                raise RuntimeError(
                    f"Coordinates must be within (0, 0) -> ({self.columns-1}, {self.rows-1})"
                )

            x_y_value = x + 64 * y

            self._set_data(
                1,
                x_y_value & 0x40,  # >> 6
                x_y_value & 0x20,  # >> 5
                x_y_value & 0x10,  # >> 4
                x_y_value & 0x08,  # >> 3
                x_y_value & 0x04,  # >> 2
                x_y_value & 0x02,  # >> 1
                x_y_value & 0x01,
            )

        self.x, self.y = x, y
        logger.debug("Moved cursor to (%s, %s)", self.x, self.y)

    def write_char(self, char: str):
        """Write a character to the display at the current cursor position.

        Args:
            char: The character to write

        """
        char_value = ord(char)

        # # Pin.value(x): The pin will be set to 1 if the value of x : bool(x) == True
        # # so no need to shift result

        self._set_data(
            char_value & 0x80,  # >> 7
            char_value & 0x40,  # >> 6
            char_value & 0x20,  # >> 5
            char_value & 0x10,  # >> 4
            char_value & 0x08,  # >> 3
            char_value & 0x04,  # >> 2
            char_value & 0x02,  # >> 1
            char_value & 0x01,
            rs=1,
        )
        logger.debug("Wrote %s", char)

        x = self.x + 1
        y = self.y
        newline = False
        if x > self.columns - 1:
            newline = True
            logger.debug("Writing newline")
            x = 0
            y += 1
            if y > self.rows - 1:
                y = 0
        self.move_to(x, y, newline)

    @api.doc("Write a string to the display")
    async def write(self, string: str):
        """Write a string to the display."""
        for char in string:
            self.write_char(char)
        return {}

    def _set_data_4_bit_mode(self, *bits, rs: int = 0):
        """Set the values of the data lines."""
        # Nibble: A 4 bit sequence
        for nibble in (bits[:4], bits[4:8]):
            if nibble:
                for idx, bit in zip(range(1, len(self._data_pins) + 1), nibble):
                    self._data_pins[-1 * idx].value(bit)
                self._rs.value(rs)
                self._enable()

    @api.doc("clear the display")
    async def clear(self):
        self._set_data(
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
        )
        sleep_us(HD44780U_LCD_CLEAR_SLEEP_TIME)
        self.move_to(0, 0, False)
        return {}

    async def _reset(self):
        """Reset the LCD by instruction."""

        await asyncio.sleep_ms(40)  # Wait for VCC to raise

        # Reset three times
        for sleep_time in [
            4100,
            100,
            100,
        ]:
            self._set_data(
                0,
                0,
                1,
                1,
            )
            sleep_us(sleep_time)

        # Function set
        # Set the data bus size, the number of rows and the font
        # 0 0 1 DL
        # 0 0 1 DL N F * *
        # N: number of lines in display (0: 1, 1: 2)
        # F: Font (0: 5x8 characters, 1: 5x10/5x11 characters)
        # DL: data line: (0: 4-bit, 1: 8-bit)
        # First nibble is transmitted twice to get the driver out of
        # 8-bit operation
        self._set_data(
            0,
            0,
            1,
            0,
        )
        self._set_data(
            0,
            0,
            1,
            0,
            bool(self.rows - 1),
            0,
            0,
            0,
        )

        # Display on
        # 0 0 0 0 1 D C B
        # D: Display on/off (0: off, 1: on)
        # C: Show cursor (0: hide, 1: show)
        # B: Blink cursor (0: steady, 1: blink)
        self._set_data(
            0,
            0,
            0,
            0,
            1,
            1,
            self.show_cursor,
            self.blink_cursor,
        )

        # Display clear
        await self.clear()

        # Entry mode set
        # 0 0 0 0 0 1 I/D S
        # I/D: Direction of the cursor (0: cursor moves left, 1: cursor moves right)
        # S: Shift the display (right: I/D==1, left: I/D==2) when S==1
        self._set_data(
            0,
            0,
            0,
            0,
            0,
            1,
            1,
            0,
        )

        if self._default_string:
            await self.write(self._default_string)

    async def _loop(self, **_):
        await self._reset()
