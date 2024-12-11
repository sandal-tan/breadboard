"""Interact with a network."""

from time import sleep

from network import (
    WLAN,
    STA_IF,
    AP_IF,
    hostname as hostname_,
)  # pyright: ignore [reportMissingImports]

from .logging import logger

WIFI_MODES = ("client", "ap")

AP_NETWORK_DEFAULT_NAME = "breadboard"
AP_NETWORK_DEFAULT_PASSWORD = "cheeseplate"
DEFAULT_PORT = 80
ALLOWABLE_HOSTS = "0.0.0.0"

DEFAULT_RETRIES = 5
RETRY_SCALING_FACTOR = 2


class Network:
    """ "Manage the Pico's network configuration.

    Args:
        ssid: The name of the network. If ``mode`` is `client`, then it will connect to this network. If ``mode`` is `ap`, this is the name of the created network
        password: The password for the network.
        mode: What mode the network should be put in. `client` if you are connecting to an existing network or `ap` if you are creating one
        port: The port on which the API should run
        hosts: Hosts allowed to access this service
        hostname: A hostname for the device

    """

    def __init__(
        self,
        ssid=None,
        password=None,
        mode=None,
        port=DEFAULT_PORT,
        hosts=ALLOWABLE_HOSTS,
        hostname="breadboard",
    ):
        hostname_(hostname)
        logger.info("Device hostname: %s", hostname)
        if not ssid:
            mode = WIFI_MODES[1]  # AP mode by default if no SSID given
        elif mode is None:
            mode = WIFI_MODES[0]

        if mode == WIFI_MODES[0]:
            for idx in range(DEFAULT_RETRIES):
                self._network = WLAN(
                    STA_IF
                )  # pyright: ignore [reportGeneralTypeIssues]
                self._network.active(True)
                self._network.connect(
                    ssid,
                    password or None,
                )
                sleep(
                    0.5
                    * (
                        (1 + idx)
                        + (idx / ((DEFAULT_RETRIES - 1) / RETRY_SCALING_FACTOR))
                    )
                )
                if self._network.isconnected():
                    logger.info(f"Connected to {ssid} at {self._network.ifconfig()[0]}")
                    break
                logger.debug(
                    *(
                        ("Retrying network connection %d/%d", idx + 2, DEFAULT_RETRIES)
                        if idx < DEFAULT_RETRIES - 1
                        else ("Cannot connect to network `%s`", ssid)
                    )
                )
            else:
                mode = WIFI_MODES[1]
                ssid = hostname
                password = ""

        if mode == WIFI_MODES[1]:
            self._network = WLAN(AP_IF)  # pyright: ignore [reportGeneralTypeIssues]
            ssid = ssid or AP_NETWORK_DEFAULT_NAME
            password = password or AP_NETWORK_DEFAULT_PASSWORD
            self._network.config(
                essid=ssid,
                password=password,
            )
            self._network.active(True)
            logger.info(
                f"Created network {ssid}, device at {self._network.ifconfig()[0]}"
            )
            logger.debug('Password is "%s"', password)
        elif mode != WIFI_MODES[0]:
            raise Exception(f"Unknown WiFi Mode: {mode}")

        while self._network.active() == False:
            pass
            sleep(0.5)

        self.port = port
        self.hosts = ALLOWABLE_HOSTS
