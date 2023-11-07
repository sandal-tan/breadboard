from utime import sleep_ms, sleep_us  # pyright: ignore [reportMissingImports]

from machine import Pin  # pyright: ignore [reportMissingImports]

from .api import api
from .base import BaseDevice


class HD44780U_LCD(BaseDevice):
    """An HD44780U-based LCD.

    Args:
        register_select_pin: The GPI pin to which the register select (RS) is connected
        enable_pin: The GPI pin to LCD's enable pin is connected
        data_pins: The pins to which the data lines. To work properly, the pins must be in
            order of their data line (DB0-DB7 or DB4-DB7)).
        columns: The number of columns on the display
        rows: The number of rows on the display

    Notes:
        - https://cdn-shop.adafruit.com/datasheets/HD44780.pdf
        - https://www.sparkfun.com/datasheets/LCD/HD44780.pdf

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
    ):
        self._rs = Pin(register_shift_pin, Pin.OUT)
        self._e = Pin(enable_pin, Pin.OUT)

        self._mode = HD44780U_LCD.UNKNOWN_MODE
        self.columns = columns
        self.rows = rows

        self.show_cursor = show_cursor
        self.blink_cursor = blink_cursor

        if len(data_pins) == 4:
            self._mode = HD44780U_LCD.FOUR_BIT_MODE
            self._data_pins = []
            for pin in data_pins:
                p = Pin(pin, Pin.OUT)
                self._data_pins.append(p)

        else:
            raise RuntimeError("Only 4-bit mode is supported.")

        self._busy_pin = self._data_pins[-1]

        super().__init__(name, api)

        self._reset()

        self._rs.value(1)
        self._set_data(0, 1, 0, 0)
        self._set_data(1, 0, 0, 0)
        # self._rs.value(0)

    def _enable(self):
        """Start the read/write cycle."""
        self._e.value(0)
        sleep_us(1)
        self._e.value(1)
        sleep_us(1)
        self._e.value(0)
        sleep_us(40)

    def _set_data(self, *bits):
        """Set the values of the data lines."""
        for idx, bit in zip(range(1, len(self._data_pins) + 1), bits):
            self._data_pins[-1 * idx].value(bit)
        self._enable()

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
        # TODO: Do I need to worry about 5x10 characters?
        self._set_data(0, 0, 1, 0)
        self._set_data(int(bool(self.rows)), 0, 0, 0)

        # Display on
        # 0 0 0 0
        # 1 D C B
        # D: Display on/off (0: off, 1: on)
        # C: Show cursor (0: hide, 1: show)
        # B: Blink cursor (0: steady, 1: blink)
        self._set_data(0, 0, 0, 0)
        self._set_data(1, 1, int(self.show_cursor), int(self.blink_cursor))

        # Display clear
        self._set_data(0, 0, 0, 0)
        self._set_data(0, 0, 0, 1)

        # Entry mode set
        # 0 0 0   0
        # 0 1 I/D S
        # I/D: Direction of the cursor (0: cursor moves left, 1: cursor moves right)
        # S: Shift the display (right: I/D==1, left: I/D==2) when S==1
        self._set_data(0, 0, 0, 0)
        self._set_data(0, 1, 1, 0)
