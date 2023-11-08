import uasyncio as asyncio  # pyright: ignore [reportMissingImports]
from utime import sleep_ms, sleep_us  # pyright: ignore [reportMissingImports]

from machine import Pin  # pyright: ignore [reportMissingImports]

from .api import api
from .base import BaseDevice

HD44780U_LCD_CLEAR_SLEEP_TIME: int = 4100
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

    """

    UNKNOWN_MODE = 0
    FOUR_BIT_MODE = 1

    def __init__(
        self,
        name,
        register_shift_pin: int,
        enable_pin: int,
        data_pins: list[int],
        columns: int = 16,
        rows: int = 2,
        show_cursor: bool = False,
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
            self._data_pins = []
            for pin in data_pins:
                p = Pin(pin, Pin.OUT, value=0)
                self._data_pins.append(p)

        else:
            raise RuntimeError("Only 4-bit mode is supported.")

        super().__init__(name, api)

        self.x = None
        self.y = None
        self._reset()
        if default_string:
            asyncio.run(self.write(default_string))

        self.group.route("/clear")(self.clear)
        self.group.route("/write")(self.write)

    def _enable(self):
        """Start the read/write cycle."""
        self._e.value(0)
        sleep_us(1)
        self._e.value(1)
        sleep_us(1)
        self._e.value(0)
        sleep_us(40)

    async def write_char(self, char: str):
        """Write a character to the display at the current cursor position.

        Args:
            char: The character to write

        """
        self._rs.value(1)
        char_value = ord(char)
        if self._mode == HD44780U_LCD.FOUR_BIT_MODE:
            # nibble: a 4-bit sequence
            for nibble in [char_value >> 4, char_value]:
                # Pin.value(x): The pin will be set to 1 if the value of x : bool(x) == True
                # so no need to shift result
                self._set_data(
                    nibble & 0x08,  # >> 3
                    nibble & 0x04,  # >> 2
                    nibble & 0x02,  # >> 1
                    nibble & 0x01,
                )

        self.x += 1

        if self.x >= self.columns:
            self.x = 0
            self.y += 1
            if self.y >= self.rows:
                self.y = 0
                # TODO: go home

    @api.doc("Write a string to the display")
    async def write(self, string: str):
        """Write a string to the display."""
        for char in string:
            await self.write_char(char)
        return {"written": string}

    def _set_data(self, *bits):
        """Set the values of the data lines."""
        for idx, bit in zip(range(1, len(self._data_pins) + 1), bits):
            self._data_pins[-1 * idx].value(bit)
        self._enable()

    @api.doc("clear the display")
    async def clear(self):
        self._rs.value(0)
        self._set_data(0, 0, 0, 0)
        self._set_data(0, 0, 0, 1)
        sleep_us(4100)
        self.x = 0
        self.y = 0
        return {"clear": True}

    def _reset(self):
        """Reset the LCD by instruction."""

        sleep_ms(40)  # Wait for VCC to raise

        # Reset three times
        for sleep_time in [4100, 100, 100]:
            self._set_data(0, 0, 1, 1)
            sleep_us(sleep_time)

        # Function set
        # Set the data bus size
        # 0 0 DL 0
        # DL: data line: (1: 4-bit, 0: 8-bit)
        self._set_data(0, 0, 1, 0)

        # Set the number of rows and the font
        # 0 0 1 0
        # N F * *
        # N: number of lines in display (0: 1, 1: 2)
        # F: Font (0: 5x8 characters, 1: 5x10 characters)
        self._set_data(0, 0, 1, 0)
        self._set_data(bool(self.rows), 0, 0, 0)

        # Display on
        # 0 0 0 0
        # 1 D C B
        # D: Display on/off (0: off, 1: on)
        # C: Show cursor (0: hide, 1: show)
        # B: Blink cursor (0: steady, 1: blink)
        self._set_data(0, 0, 0, 0)
        self._set_data(1, 1, self.show_cursor, self.blink_cursor)

        # Display clear
        asyncio.run(self.clear())
        # self._set_data(0, 0, 0, 0)
        # self._set_data(0, 0, 0, 1)
        # sleep_us(4100)

        # Entry mode set
        # 0 0 0   0
        # 0 1 I/D S
        # I/D: Direction of the cursor (0: cursor moves left, 1: cursor moves right)
        # S: Shift the display (right: I/D==1, left: I/D==2) when S==1
        self._set_data(0, 0, 0, 0)
        self._set_data(0, 1, 1, 0)
