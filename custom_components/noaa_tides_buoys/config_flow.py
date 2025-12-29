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
    
    # Create appropriate client based on data source
    if data_source == DATA_SOURCE_TIDES:
        client = TidesApiClient(session)
    else:
        client = BuoyApiClient(session)
    
    # Validate station exists
    valid = await client.validate_station(station_id)
    if not valid:
        raise ValueError("Invalid station ID")
    
    # Try to get station name
    station_name = await client.get_station_name(station_id)
    
    # Create title with source prefix and station name/ID
    source_name = data_source.replace('_', ' ').title()
    if station_name:
        title = f"NOAA {source_name} - {station_name}"
    else:
        title = f"NOAA {source_name} - {station_id}"
    
    return {"title": title}


class NOAAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NOAA Tides and Buoys."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._data = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - select data source."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            self._data = user_input
            return await self.async_step_station()

        # Select data source
        data_schema = vol.Schema(
            {
                vol.Required(CONF_DATA_SOURCE): vol.In(
                    {
                        DATA_SOURCE_TIDES: "Tides and Currents",
                        DATA_SOURCE_BUOY: "Buoy Data",
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_station(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle station selection step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_data_type()

        # Enter station ID
        data_schema = vol.Schema(
            {
                vol.Required(CONF_STATION_ID): str,
            }
        )

        return self.async_show_form(
            step_id="station", data_schema=data_schema, errors=errors
        )

    async def async_step_data_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle data type selection step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            self._data.update(user_input)
            
            # Check if this station is already configured
            await self.async_set_unique_id(
                f"{self._data[CONF_DATA_SOURCE]}_{self._data[CONF_STATION_ID]}_{self._data[CONF_DATA_TYPE]}"
            )
            self._abort_if_unique_id_configured()
            
            try:
                info = await validate_input(self.hass, self._data)
            except ValueError:
                errors["base"] = "invalid_station"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=self._data)

        # Select appropriate data types based on data source
        if self._data[CONF_DATA_SOURCE] == DATA_SOURCE_TIDES:
            data_types = TIDES_PRODUCTS
        else:
            data_types = BUOY_DATA_TYPES

        data_schema = vol.Schema(
            {
                vol.Required(CONF_DATA_TYPE): vol.In(data_types),
            }
        )

        return self.async_show_form(
            step_id="data_type", data_schema=data_schema, errors=errors
        )
