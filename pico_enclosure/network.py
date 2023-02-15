"""Interact with a network."""

from time import sleep

from network import WLAN, STA_IF, AP_IF  # pyright: ignore [reportMissingImports]

WIFI_MODES = ("client", "ap")

AP_NETWORK_DEFAULT_NAME = "pico-print"
AP_NETWORK_DEFAULT_PASSWORD = "rocky-racoon"


class Network:
    """ "Manage the Pico's network configuration.

    Args:
        ssid: The name of the network. If ``mode`` is `client`, then it will connect to this network. If ``mode`` is `ap`, this is the name of the created network
        password: The password for the network.
        mode: What mode the network should be put in. `client` if you are connecting to an existing network or `ap` if you are creating one

    """

    def __init__(self, ssid=None, password=None, mode=None):
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
