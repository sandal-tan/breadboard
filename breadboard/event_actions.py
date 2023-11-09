from asyncio import open_connection  # pyright: ignore
import socket
import re
from .logging import logger, _exception_to_str

URL_PATTERN = re.compile(r"(http[s]?)://(.*?):?(\d*)(/.*)")


class Webhook:
    """Make an HTTP GET request.

    Args:
        The URL of the webhook

    """

    def __init__(self, url, **_) -> None:
        match = URL_PATTERN.match(url)
        if match is not None:
            self._method = match.group(1)
            self._host = match.group(2)
            self._port = match.group(3)
            self._path = match.group(4)

            self._port = int(self._port) if self._port else 80
            self._socket = socket.socket()

        else:
            raise RuntimeError("Could not parse address")

    async def __call__(self):
        # TODO reuse connection
        try:
            _socket = socket.socket()
            _socket.settimeout(1.0)
            _socket.connect(socket.getaddrinfo(self._host, self._port)[0][-1])
            request = f"GET {self._path} HTTP/1.1\r\n\r\n"
            logger.debug(f"Sending `{repr(request)}` to {self._host}:{self._port}")
            _socket.write(request.encode())  # pyright: ignore
            _socket.close()
        except OSError as e:
            logger.error(_exception_to_str(e))


class DeviceAction:
    """Execute a device action on an event.

    Args:
        name: The name of the device
        action: The action to take with the device
        devices: The devices present on the microcontroller
        kwargs: Keyword arguments passed to ``name.action``

    """

    def __init__(self, name, action, devices, **kwargs):
        self._func = getattr(devices[name], action)
        self._kwargs = kwargs

    async def __call__(self):
        await self._func(**self._kwargs)


EVENT_ACTIONS = {"webhook": Webhook, "device": DeviceAction}


def parse_event_actions(raw_json, devices):
    """Parse a JSON object for event actions.

    Args:
        raw_json: The JSON object containing an event action
        devices: The devices present on the microcontroller

    Returns:
        A list of actions for a given state

    """
    event_actions = []
    if isinstance(raw_json, dict):
        raw_json = [raw_json]

    for action in raw_json:
        for action, arguments in action.items():
            event_actions.append(EVENT_ACTIONS[action](**arguments, devices=devices))

    return event_actions
