"""Base objects."""


from .logging import logger


class BaseDevice:
    """Base behavior of all attached devices."""

    def __init__(self, name, logger):
        self.name = name
        self.logger = logger

    async def _loop(self):
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
