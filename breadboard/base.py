"""Base objects."""

from .logging import logger


class BaseDevice:
    """Base behavior of all attached devices."""

    __doc__ = None

    def __init__(self, name, api):
        self.name = name
        self.group = api.register(self.name, self)

    async def _loop(self, **_):
        return

    @classmethod
    def try_to_instantiate(cls):
        """Provider a optional constructor for the class, logging an errors."""

        def _init(*args, **kwargs):
            try:
                return cls(*args, **kwargs)
            except Exception as e:
                logger.error(e, name=cls.__name__)

        return _init


class StatefulDevice(BaseDevice):
    """A device which manages states. Can be used to trigger events."""

    __doc__ = None

    _states = None

    def __init__(self, name, api):
        self._state = None
        # self.manage_state = lambda: None
        super().__init__(name, api)

        self.group.route("/state")(self.get_state)

    @property
    def state(self):
        """Get the current state of a device."""
        if self._state == None:
            raise RuntimeError("A state must be set")
        return self._state

    @property
    def states(self):
        """Get the possible states of the device."""
        if self._states is None:
            raise RuntimeError("Possible states must be given")
        return self._states

    async def process_events(self, events: dict[str, dict[str, list]]):
        """Process the events for this device.

        Notes:
            This should be called during the overridden `_loop` function
            defined on the implemented device.

        Events: The collection of events

        """
        await self.manage_state()
        # TODO validate state in events are valid for device
        for event_action in events.get(self.name, {}).get(self.state, []):
            await event_action()

    async def get_state(self):
        return {"state": self.state}
