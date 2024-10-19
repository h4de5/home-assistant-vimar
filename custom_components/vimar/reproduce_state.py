from typing import Iterable, Optional
from homeassistant.core import Context, State
from homeassistant.core import HomeAssistant

# https://developers.home-assistant.io/docs/reproduce_state_index/

# see: https://git.edevau.net/Ede_Vau/home-assistant-core/src/branch/dev/script/scaffold/templates/reproduce_state/integration/reproduce_state.py


from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)

from . import DOMAIN

# _LOGGER = logging.getLogger(__name__)

# # TODO add valid states here
# VALID_STATES = {STATE_ON, STATE_OFF}


# async def async_reproduce_states(
#     hass: HomeAssistant,
#     states: Iterable[State],
#     *,
#     context: Optional[Context] = None,
#     reproduce_options: Optional[Dict[str, Any]] = None,
# ) -> None:
#     """Reproduce NEW_NAME states."""
#     # TODO pick one and remove other one

#     # Reproduce states in parallel.
#     await asyncio.gather(
#         *(
#             _async_reproduce_state(
#                 hass, state, context=context, reproduce_options=reproduce_options
#             )
#             for state in states
#         )
#     )


# async def _async_reproduce_state(
#     hass: HomeAssistant,
#     state: State,
#     *,
#     context: Optional[Context] = None,
#     reproduce_options: Optional[Dict[str, Any]] = None,
# ) -> None:
#     """Reproduce a single state."""
#     cur_state = hass.states.get(state.entity_id)

#     if cur_state is None:
#         _LOGGER.warning("Unable to find entity %s", state.entity_id)
#         return

#     if state.state not in VALID_STATES:
#         _LOGGER.warning(
#             "Invalid state specified for %s: %s", state.entity_id, state.state
#         )
#         return

#     # Return if we are already at the right state.
#     if (
#         cur_state.state == state.state
#         and
#         # TODO this is an example attribute
#         cur_state.attributes.get("color") == state.attributes.get("color")
#     ):
#         return

#     service_data = {ATTR_ENTITY_ID: state.entity_id}

#     # TODO determine the services to call to achieve desired state
#     if state.state == STATE_ON:
#         service = SERVICE_TURN_ON
#         if "color" in state.attributes:
#             service_data["color"] = state.attributes["color"]

#     elif state.state == STATE_OFF:
#         service = SERVICE_TURN_OFF

#     await hass.services.async_call(
#         DOMAIN, service, service_data, context=context, blocking=True
#     )

async def async_reproduce_states(
    hass: HomeAssistant, states: Iterable[State], context: Optional[Context] = None
) -> None:
    """Reproduce component states."""
    # TODO reproduce states


# # Reproduce states in parallel.
#     await asyncio.gather(
#         *(_async_reproduce_state(hass, state, context) for state in states)
#     )
