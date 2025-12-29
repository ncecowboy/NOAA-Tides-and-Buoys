"""Config flow for NOAA Tides and Buoys integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_DATA_SOURCE,
    CONF_STATION_ID,
    CONF_DATA_TYPE,
    DATA_SOURCE_TIDES,
    DATA_SOURCE_BUOY,
    TIDES_PRODUCTS,
    BUOY_DATA_TYPES,
)
from .tides_api import TidesApiClient
from .buoy_api import BuoyApiClient

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass)
    
    data_source = data[CONF_DATA_SOURCE]
    station_id = data[CONF_STATION_ID]
    
    if data_source == DATA_SOURCE_TIDES:
        client = TidesApiClient(session)
        valid = await client.validate_station(station_id)
    else:
        client = BuoyApiClient(session)
        valid = await client.validate_station(station_id)
    
    if not valid:
        raise ValueError("Invalid station ID")
    
    return {"title": f"NOAA {data_source.replace('_', ' ').title()} - {station_id}"}


class NOAAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NOAA Tides and Buoys."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # Check if this station is already configured
            await self.async_set_unique_id(
                f"{user_input[CONF_DATA_SOURCE]}_{user_input[CONF_STATION_ID]}"
            )
            self._abort_if_unique_id_configured()
            
            try:
                info = await validate_input(self.hass, user_input)
            except ValueError:
                errors["base"] = "invalid_station"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        # Build the schema with dynamic data type options
        data_schema = vol.Schema(
            {
                vol.Required(CONF_DATA_SOURCE): vol.In(
                    {
                        DATA_SOURCE_TIDES: "Tides and Currents",
                        DATA_SOURCE_BUOY: "Buoy Data",
                    }
                ),
                vol.Required(CONF_STATION_ID): str,
                vol.Required(CONF_DATA_TYPE): vol.In(
                    {**TIDES_PRODUCTS, **BUOY_DATA_TYPES}
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
