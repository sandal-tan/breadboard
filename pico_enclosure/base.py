"""Base objects."""


class BaseDevice:
    """Base behavior of all attached devices."""

    def __init__(self, name, logger):
        self.name = name
        self.logger = logger

    async def _loop(self):
        return
