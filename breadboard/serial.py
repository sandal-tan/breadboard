"""Serial Interface."""

import asyncio
from machine import UART  # pyright: ignore

from .api import api
from .base import BaseDevice


class Serial(BaseDevice):
    """Create a serial device.

    Notes:
        Connection is read from during `Serial._loop` via the function passed to `on_read`.
        If no callback is given, then the loop will terminate.

    Args:
        name: A name for the serial device
        uart_id: The UART peripheral to use (0, 1)
        baudrate: The baudrate for the connection
        tx_pin: The number of the TX pin to use for the UART device
        rx_pin: The number of the RX pin to use for the UART device
        bits: The number of bits per character (7, 8, 9)
        parity_bit: The parity (None, 0, 1)
        stop_bits: The number of stop bits (1, 2)
        timeout: The number of seconds to wait for the first character (ms)
        on_read: A callback to perform when a line of data is ready from the connection.

    Source:
        https://docs.micropython.org/en/v1.15/library/machine.UART.html

    """

    def __init__(
        self,
        name,
        uart_id,
        baudrate: int = 115200,
        tx_pin: int = None,
        rx_pin: int = None,
        bits: int = 8,
        parity_bit: int = None,
        stop_bits: int = 1,
        timeout: int = 5000,
        on_read=None,
    ):
        super().__init__(name, api)
        self._on_read = on_read

        self._uart = UART(uart_id, baudrate)
        self._uart.init(
            baudrate=baudrate,
            bits=bits,
            parity=parity_bit,
            stop=stop_bits,
            tx=tx_pin,
            rx=rx_pin,
            timeout=timeout,
        )

        self.group.route("/write")(self.write)

    @api.doc(
        """Write data to the connected serial device.

        Args:
            data: The data to write

        """
    )
    async def write(self, *, data: str):
        bytes_written = self._uart.write(
            f"{data}\n".encode(),
        )
        return {"bytes_written": bytes_written}

    async def _loop(self, **_):
        if self._on_read is not None:
            while True:
                while self._uart.any() and (line := self._uart.readline()) is not None:
                    self._on_read(line)
                await asyncio.sleep(0.1)
