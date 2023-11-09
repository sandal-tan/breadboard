"""Interact with a network."""

from time import sleep

from network import WLAN, STA_IF, AP_IF  # pyright: ignore [reportMissingImports]

from .logging import logger

WIFI_MODES = ("client", "ap")

AP_NETWORK_DEFAULT_NAME = "breadboard"
AP_NETWORK_DEFAULT_PASSWORD = "cheesplate"
DEFAULT_PORT = 80
ALLOWABLE_HOSTS = "0.0.0.0"


class Network:
    """ "Manage the Pico's network configuration.

    Args:
        ssid: The name of the network. If ``mode`` is `client`, then it will connect to this network. If ``mode`` is `ap`, this is the name of the created network
        password: The password for the network.
        mode: What mode the network should be put in. `client` if you are connecting to an existing network or `ap` if you are creating one
        port: The port on which the API should run
        hosts: Hosts allowed to access this service

    """

    def __init__(
        self,
        ssid=None,
        password=None,
        mode=None,
        port=DEFAULT_PORT,
        hosts=ALLOWABLE_HOSTS,
    ):
        if not ssid:
            mode = WIFI_MODES[1]  # AP mode by default if no SSID given
        elif mode is None:
            mode = WIFI_MODES[0]

        if mode == WIFI_MODES[0]:
            self._network = WLAN(STA_IF)  # pyright: ignore [reportGeneralTypeIssues]
            self._network.active(True)
            self._network.connect(
                ssid,
                password or None,
            )
            logger.info(f"Connected to {ssid} at {self._network.ifconfig()[0]}")
        elif mode == WIFI_MODES[1]:
            self._network = WLAN(AP_IF)  # pyright: ignore [reportGeneralTypeIssues]
            self._network.config(
                essid=ssid or AP_NETWORK_DEFAULT_NAME,
                password=password or AP_NETWORK_DEFAULT_PASSWORD,
            )
            self._network.active(True)
        else:
            raise Exception(f"Unknown WiFi Mode: {mode}")

        while self._network.active() == False:
            pass
            sleep(0.5)

        self.port = port
        self.hosts = ALLOWABLE_HOSTS
