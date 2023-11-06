"""Serial Interface."""

from machine import UART  # pyright: ignore

from .api import api
from .base import BaseDevice


class Serial(BaseDevice):
    """Create a serial device.

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

    Source:
        https://docs.micropython.org/en/v1.15/library/machine.UART.html

    """

    def __init__(
        self,
        name,
        uart_id,
        baudrate: int = 9600,
        tx_pin: int = None,
        rx_pin: int = None,
        bits: int = 8,
        parity_bit: int = None,
        stop_bits: int = 1,
        timeout: int = 5000,
    ):
        super().__init__(name, api)

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
            message: The message to write

        """
    )
    async def write(self, *, message: str):
        bytes_written = self._uart.write(
            f"{message}\n".encode(),
        )
        return {"bytes_written": bytes_written}
