"""Base objects."""
import uasyncio as asyncio  # pyright: ignore


from .logging import logger


class BaseDevice:
    """Base behavior of all attached devices."""

    __doc__ = None

    def __init__(self, name, api):
        self.name = name
        self.group = api.register(self.name, self)

    async def _loop(self, **kwargs):
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
        self.on_state_change = lambda: None
        super().__init__(name, api)

        self.group.route("/state")(self.get_state)

    @property
    def state(self):
        if self._state == None:
            raise RuntimeError("A state must be set")
        return self._state

    @property
    def states(self):
        if self._states is None:
            raise RuntimeError("Possible states must be given")
        return self._states

    async def manage_state(self, events):
        self.on_state_change()
        # TODO validate state in events are valid for device
        for event_action in events.get(self.name, {}).get(self.state, []):
            await event_action()

    async def get_state(self):
        return {"state": self.state}
