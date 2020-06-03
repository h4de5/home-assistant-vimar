import asyncio
from typing import Iterable, Optional
from homeassistant.core import Context, State
from homeassistant.helpers.typing import HomeAssistantType


async def async_reproduce_states(
    hass: HomeAssistantType, states: Iterable[State], context: Optional[Context] = None
) -> None:
    """Reproduce component states."""
    # TODO reproduce states
