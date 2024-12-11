from machine import Pin  # pyright: ignore[reportMissingImports]
import time

from .api import api
from .base import BaseDevice
from .logging import logger

# Docs
# - NEC Protocol: https://techdocs.altium.com/display/FPGA/NEC%2bInfrared%2bTransmission%2bProtocol
#
#  |-+         +-----+
#  | |         |     |
#  | |         |     |
#  | +---------+     +-
#  > |--- a ---|- b -|
#
# a) The signal begins with a 9ms pulse
# b) Following the initial pulse, there is a 4.5ms delay until the next pulse
#
# After the initial pulse and delay, 4 bytes are sent where:
#
#  |-+ +---+ +---------+
#  | | |   | |         |
#  | | |   | |         |
#  | +-+   +-+         +-
#  > |- c -|---- d ----|
#
# c) Logical `0`: a 562.5µs pulse followed by a 562.5µs pulse delay [total: 1.125ms]
# d) Logical `1`: a 562.5µs pulse followed by a 1.6875ms pulse delay [total: 2.25ms]
#
# Bytes values are passed little-endian sequentially, with no delay between individual bytes or bits.
#
# The 4 bytes that are received are:
#
# 1.  Receiver address
# 2. Inverted receiver address
# 3. Command
# 4. Invereted command
#
# The inverted values `2` and `4` are used as a check against the values `1` and `3`.
#
# In the event that the `NEC Extended` protocol is being used, bytes `2` and `4` are instead the most-significant
# byte when paired with `1` and `3` repsectively. `NEC Extended` is a 16-bit protocol, where as `NEC` is only 8-bit.
#
# After the 4 bytes are received, a final 562.5µs pulse is sent to indicate the end of the packet. Over the course of
# the packet, there are 34 pulses (68 edges) made:
# 1     -> Initial 9ms pulse
# 2-9   -> Receiver address bits
# 10-17 -> Inverted receiver address bits
# 18-25 -> Command bits
# 26-33 -> Inverted command bits
# 34    -> Terminal 562.5µs pulse

NEC_START_PULSE_LENGTH = 4000
NEC_START_PULSE_LENGTH_MIN_BOUND = NEC_START_PULSE_LENGTH * 0.975
NEC_START_PULSE_LENGTH_MAX_BOUND = NEC_START_PULSE_LENGTH * 1.025

NEC_INITIAL_PAUSE_LENGTH = 3000
NEC_INITIAL_PAUSE_LENGTH_MIN_BOUND = NEC_INITIAL_PAUSE_LENGTH * 0.975
NEC_INITIAL_PAUSE_LENGTH_MAX_BOUND = NEC_INITIAL_PAUSE_LENGTH * 1.025

NEC_PULSE_BURST_LENGTH = 562
NEC_PULSE_BURST_LENGTH_MIN_BOUND = NEC_PULSE_BURST_LENGTH * 0.95
NEC_PULSE_BURST_LENGTH_MAX_BOUND = NEC_PULSE_BURST_LENGTH * 1.05

NEC_1_BIT_PULSE_LENGTH = 1125
NEC_1_BIT_PULSE_LENGTH_MIN_BOUND = NEC_1_BIT_PULSE_LENGTH * 0.95


class IRReceiver(BaseDevice):

    def __init__(self, *, name: str, pin: int):
        self.pin = Pin(pin, Pin.IN)

        self.pin.irq(self.on_pulse, Pin.IRQ_RISING | Pin.IRQ_FALLING)

        super().__init__(name, api)

        self.expected_events = 68
        self.max_tranmission_length = 120 * 1000

        self.events = []
        self.last_event_at = None

        self.last_state = None

    def process_events(self):
        events = self.events

        self.events = []
        self.last_event_at = None

        try:

            if len(events) > self.expected_events:
                logger.error("Captured more events than expected")
                return

            # ~9000ms pause
            if not (NEC_START_PULSE_LENGTH_MIN_BOUND <= events[1][-1]):
                logger.error(
                    "Initial pulse duration was out of bounds: %d", events[1][-1]
                )
                return

            # # ~562.5µs pulse to end packet
            # if not (
            # NEC_PULSE_BURST_LENGTH_MIN_BOUND
            # <= events[-1][-1]
            # <= NEC_PULSE_BURST_LENGTH_MAX_BOUND
            # ):
            # logger.error(
            # "Terminal pulse duration was out of bounds: %d", events[-1][-1]
            # )
            # return

            # ~4500ms for a normal command
            if NEC_INITIAL_PAUSE_LENGTH_MIN_BOUND <= events[2][-1]:

                if (
                    bytes_ := [
                        int(
                            "".join(
                                [
                                    (
                                        "1"
                                        if NEC_1_BIT_PULSE_LENGTH_MIN_BOUND <= elem[-1]
                                        else "0"
                                    )
                                    for elem in _slice
                                ]
                            ),
                            2,
                        )
                        for _slice in (
                            # Bits are little-endian
                            events[18:3:-2],  # address
                            events[34:19:-2],  # inverse address
                            events[50:35:-2],  # command
                            events[66:51:-2],  # inverse command
                        )
                    ]
                )[0] | bytes_[1] == 0xFF:
                    protocol = "NEC"
                    address = bytes_[0]
                    if (bytes_[2] | bytes_[3]) == 0xFF:
                        command = bytes_[2]
                    else:
                        logger.error("Command validation failed")
                        return
                else:
                    protocol = "NEC Extended"
                    address = bytes_[1] << 8 | bytes_[0]
                    command = bytes_[3] << 8 | bytes_[2]

                logger.info(
                    address="0x%02x" % address,
                    command="0x%02x" % command,
                    protocol=protocol,
                    device=self.name,
                )
            else:
                logger.error("Pause out of bounds: %d", events[2][-1])
                return
        except Exception as e:
            logger.error(e)
        finally:
            return

    def on_pulse(self, pin: Pin):
        state = "end" if pin.value() else "start"
        event_at = time.ticks_us()

        if state != self.last_state:

            self.events.append(
                (
                    event_at,
                    state,
                    (
                        (event_diff := time.ticks_diff(event_at, self.last_event_at))
                        if self.last_event_at
                        else None
                    ),
                )
            )

            # TODO look at max events/duration to reset after too many/long
            # Maybe use duration to trigger processing for a repeat code
            if len(self.events) >= self.expected_events or (
                self.last_event_at is not None
                and event_diff >= self.max_tranmission_length
            ):
                self.process_events()
            else:
                self.last_event_at = event_at

            self.last_state = state
